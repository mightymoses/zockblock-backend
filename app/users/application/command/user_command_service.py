import uuid
from typing import Literal
import structlog
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session
from app.common import storage
from app.terms.application.query import terms_query_service
from app.users import repository
from app.users.exceptions import (
    InvalidAvatarModeException,
    InvalidAvatarUrlException,
    OutdatedTermsVersionException,
    UsernameAlreadyTakenException,
)
from app.users.models import TermsAcceptance, User, get_datetime_utc

logger = structlog.get_logger()

# maps the content types accepted by the avatar upload endpoint to a file extension
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def create_user(
    session: Session,
    username: str,
    external_auth_id: str,
    crash_reports_consent: bool,
    accepted_terms_version: str,
    animal_asset_name: str | None = None,
    avatar_color: int | None = None,
    bio: str | None = None,
    avatar_url: str | None = None,
    avatar_mode: Literal["animal", "photo"] = "animal",
) -> User:
    _validate_terms_version(accepted_terms_version)
    pending_avatar_key = (
        _pending_avatar_key(avatar_url, external_auth_id) if avatar_url is not None else None
    )

    if repository.exists_by_username(session, username):
        raise UsernameAlreadyTakenException()

    user = User(
        username=username,
        external_auth_id=external_auth_id,
        animal_asset_name=animal_asset_name,
        avatar_color=avatar_color,
        bio=bio,
        avatar_url=avatar_url,
        avatar_mode=avatar_mode,
        crash_reports_consent=crash_reports_consent,
        crash_reports_consent_updated_at=get_datetime_utc(),
    )
    user.terms_acceptances.append(TermsAcceptance(user_id=user.id, terms_version=accepted_terms_version))
    _validate_avatar_mode(user)

    promoted_avatar_key = _promote_avatar(user, pending_avatar_key) if pending_avatar_key else None

    _save_and_clean_up_avatars(session, user, promoted_avatar_key, replaced_avatar_url=None)
    session.refresh(user)

    logger.info("user created", user_id=str(user.id))

    return user


def update_user(session: Session, user: User, changes: dict[str, str | int | None]) -> User:
    changes = dict(changes)  # don't mutate the caller's dict

    # not a column on the user, but a new row in its acceptance history
    accepted_terms_version = changes.pop("accepted_terms_version", None)
    if accepted_terms_version is not None:
        _validate_terms_version(str(accepted_terms_version))

    crash_reports_consent_changed = (
        "crash_reports_consent" in changes
        and changes["crash_reports_consent"] != user.crash_reports_consent
    )

    if "avatar_url" in changes and changes["avatar_url"] == user.avatar_url:
        # client just sent the unchanged URL back along with other fields - nothing to do
        del changes["avatar_url"]

    replaced_avatar_url: str | None = None
    pending_avatar_key: str | None = None
    if "avatar_url" in changes:
        replaced_avatar_url = user.avatar_url
        new_avatar_url = changes["avatar_url"]
        if new_avatar_url is not None:
            pending_avatar_key = _pending_avatar_key(str(new_avatar_url), user.external_auth_id)

    new_username = changes.get("username")
    if (
        new_username
        and new_username != user.username
        and repository.exists_by_username(session, new_username)  # pyright: ignore[reportArgumentType]
    ):
        raise UsernameAlreadyTakenException()

    for field, value in changes.items():
        setattr(user, field, value)

    if crash_reports_consent_changed:
        user.crash_reports_consent_updated_at = get_datetime_utc()
    if accepted_terms_version is not None and not user.has_accepted_terms(str(accepted_terms_version)):
        user.terms_acceptances.append(TermsAcceptance(user_id=user.id, terms_version=str(accepted_terms_version)))

    _validate_avatar_mode(user)

    promoted_avatar_key = _promote_avatar(user, pending_avatar_key) if pending_avatar_key else None

    _save_and_clean_up_avatars(session, user, promoted_avatar_key, replaced_avatar_url)
    session.refresh(user)

    logger.info("user updated", user_id=str(user.id))

    return user


def request_avatar_upload_url(external_auth_id: str, content_type: str) -> tuple[str, str]:
    """Returns (upload_url, avatar_url). Doesn't touch the database - the client
    still needs to send the resulting avatar_url via create_user/update_user for
    it to actually be saved on the profile. Until then the upload stays under the
    pending prefix, which R2 cleans up on its own."""
    extension = CONTENT_TYPE_EXTENSIONS[content_type]
    key = f"{storage.PENDING_PREFIX}avatars/{external_auth_id}/{uuid.uuid4()}.{extension}"
    return storage.generate_presigned_upload_url(key, content_type)


def _pending_avatar_key(avatar_url: str, external_auth_id: str | None) -> str:
    """Only accepts a URL from our own upload flow, uploaded by this very user -
    returns its pending storage key."""
    key = storage.key_from_public_url(avatar_url)
    owner_prefix = f"{storage.PENDING_PREFIX}avatars/{external_auth_id}/"
    if (
        key is None
        or external_auth_id is None
        or not key.startswith(owner_prefix)
        # exactly one file name below the user's folder, nothing nested
        or "/" in key.removeprefix(owner_prefix)
    ):
        raise InvalidAvatarUrlException()
    return key


def _promote_avatar(user: User, pending_key: str) -> str:
    """Copies the pending upload to its permanent location and points the user at it.
    Copy instead of move, so the pending original survives if the commit fails
    and the client can simply retry. Returns the permanent key."""
    permanent_key = pending_key.removeprefix(storage.PENDING_PREFIX)
    try:
        storage.copy_object(pending_key, permanent_key)
    except storage.StorageObjectNotFoundError as exc:
        # URL looks fine, but nothing was ever uploaded (or it already expired)
        raise InvalidAvatarUrlException() from exc
    user.avatar_url = storage.public_url_for_key(permanent_key)
    return permanent_key


def _validate_terms_version(terms_version: str) -> None:
    if terms_version != terms_query_service.get_current_terms().version:
        raise OutdatedTermsVersionException()


def _validate_avatar_mode(user: User) -> None:
    if user.avatar_mode == "photo" and user.avatar_url is None:
        raise InvalidAvatarModeException()


def _save_and_clean_up_avatars(
    session: Session, user: User, promoted_avatar_key: str | None, replaced_avatar_url: str | None
) -> None:
    """Saves the user, then deletes whichever avatar objects are no longer referenced:
    on success the pending original and the replaced avatar, on failure the
    permanent copy we just made."""
    try:
        _save_or_raise_if_username_taken(session, user)
    except Exception:
        if promoted_avatar_key:
            _delete_avatar_quietly(promoted_avatar_key)
        raise

    if promoted_avatar_key:
        _delete_avatar_quietly(storage.PENDING_PREFIX + promoted_avatar_key)
    if replaced_avatar_url:
        replaced_key = storage.key_from_public_url(replaced_avatar_url)
        if replaced_key:
            _delete_avatar_quietly(replaced_key)


def _delete_avatar_quietly(key: str) -> None:
    """A leftover object is only a storage leak, not worth failing the request for."""
    try:
        storage.delete_object(key)
    except Exception:
        logger.warning("avatar cleanup failed", key=key, exc_info=True)


def _save_or_raise_if_username_taken(session: Session, user: User) -> None:
    # repository.add() already flushes, so a unique violation can surface there - not only on commit
    try:
        repository.add(session, user)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise UsernameAlreadyTakenException() from exc
