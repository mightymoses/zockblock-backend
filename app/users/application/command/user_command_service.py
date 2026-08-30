import uuid
import structlog
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session
from app.common import storage
from app.config import get_settings
from app.users import repository
from app.users.exceptions import InvalidAvatarUrlException, UsernameAlreadyTakenException
from app.users.models import User

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
    animal_asset_name: str | None = None,
    avatar_color: int | None = None,
    bio_line_1: str | None = None,
    bio_line_2: str | None = None,
    avatar_url: str | None = None,
) -> User:
    _validate_avatar_url(avatar_url)

    if repository.exists_by_username(session, username):
        raise UsernameAlreadyTakenException()

    user = User(
        username=username,
        external_auth_id=external_auth_id,
        animal_asset_name=animal_asset_name,
        avatar_color=avatar_color,
        bio_line_1=bio_line_1,
        bio_line_2=bio_line_2,
        avatar_url=avatar_url,
    )
    repository.add(session, user)
    _commit_or_raise_if_username_taken(session)
    session.refresh(user)

    logger.info("user created", user_id=str(user.id))

    return user


def update_user(session: Session, user: User, changes: dict[str, str | int | None]) -> User:
    if "avatar_url" in changes:
        _validate_avatar_url(changes["avatar_url"])  # pyright: ignore[reportArgumentType]

    new_username = changes.get("username")
    if (
        new_username
        and new_username != user.username
        and repository.exists_by_username(session, new_username)  # pyright: ignore[reportArgumentType]
    ):
        raise UsernameAlreadyTakenException()

    for field, value in changes.items():
        setattr(user, field, value)

    repository.add(session, user)
    _commit_or_raise_if_username_taken(session)
    session.refresh(user)

    logger.info("user updated", user_id=str(user.id))

    return user


def request_avatar_upload_url(external_auth_id: str, content_type: str) -> tuple[str, str]:
    """Returns (upload_url, avatar_url). Doesn't touch the database - the client
    still needs to send the resulting avatar_url via create_user/update_user for
    it to actually be saved on the profile."""
    extension = CONTENT_TYPE_EXTENSIONS[content_type]
    key = f"avatars/{external_auth_id}/{uuid.uuid4()}.{extension}"
    return storage.generate_presigned_upload_url(key, content_type)


def _validate_avatar_url(avatar_url: str | None) -> None:
    if avatar_url is not None and not avatar_url.startswith(get_settings().r2_public_base_url):
        raise InvalidAvatarUrlException()


def _commit_or_raise_if_username_taken(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise UsernameAlreadyTakenException() from exc
