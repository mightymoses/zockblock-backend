from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.common import storage
from app.config import get_settings
from app.users.application.command import user_command_service
from app.users.models import TermsAcceptance
from tests.conftest import CURRENT_TERMS_VERSION, FakeStorage

BASE_URL = "https://pub-test.example.r2.dev"
# required on every profile creation - spread into the request bodies / service calls
CONSENTS = {"crashReportsConsent": False, "acceptedTermsVersion": CURRENT_TERMS_VERSION}
PERMANENT_AVATAR_URL = f"{BASE_URL}/avatars/auth0|test-user/1.jpg"


def _create_other_user(session: Session, username: str) -> None:
    user_command_service.create_user(
        session,
        username=username,
        external_auth_id="auth0|someone-else",
        crash_reports_consent=False,
        accepted_terms_version=CURRENT_TERMS_VERSION,
    )


def _upload_avatar(fake_storage: FakeStorage, file_name: str = "1.jpg") -> str:
    """Simulates a finished client upload - returns the pending URL the app would send."""
    key = f"pending/avatars/auth0|test-user/{file_name}"
    fake_storage.objects.add(key)
    return f"{BASE_URL}/{key}"


def test_create_and_get_current_user(client: TestClient):
    create_response = client.post("/api/users/", json={**CONSENTS, "username": "alice"})
    assert create_response.status_code == 200
    assert create_response.json()["username"] == "alice"

    get_response = client.get("/api/users/current")
    assert get_response.status_code == 200
    assert get_response.json()["username"] == "alice"


def test_get_current_user_404_when_not_registered(client: TestClient):
    response = client.get("/api/users/current")

    assert response.status_code == 404


def test_create_user_with_full_profile_fields(client: TestClient, fake_storage: FakeStorage):
    response = client.post(
        "/api/users/",
        json={
            **CONSENTS,
            "username": "alice",
            "animalAssetName": "fox",
            "avatarColor": 3,
            "bio": "Hello there. General Kenobi!",
            "avatarUrl": _upload_avatar(fake_storage),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["animalAssetName"] == "fox"
    assert body["avatarColor"] == 3
    assert body["bio"] == "Hello there. General Kenobi!"
    assert body["avatarUrl"] == PERMANENT_AVATAR_URL


def test_create_user_defaults_to_animal_mode(client: TestClient):
    response = client.post("/api/users/", json={**CONSENTS, "username": "alice"})

    assert response.status_code == 200
    assert response.json()["avatarMode"] == "animal"


def test_create_user_with_photo_mode_and_avatar_url_succeeds(
    client: TestClient, fake_storage: FakeStorage
):
    response = client.post(
        "/api/users/",
        json={
            **CONSENTS,
            "username": "alice",
            "avatarMode": "photo",
            "avatarUrl": _upload_avatar(fake_storage),
        },
    )

    assert response.status_code == 200
    assert response.json()["avatarMode"] == "photo"


def test_create_user_fails_with_photo_mode_and_no_avatar_url(client: TestClient):
    response = client.post("/api/users/", json={**CONSENTS, "username": "alice", "avatarMode": "photo"})

    assert response.status_code == 400


def test_update_user_fails_switching_to_photo_mode_without_avatar_url(client: TestClient):
    client.post("/api/users/", json={**CONSENTS, "username": "alice"})

    response = client.patch("/api/users/current", json={"avatarMode": "photo"})

    assert response.status_code == 400


def test_update_user_switching_to_animal_mode_keeps_avatar_url(
    client: TestClient, fake_storage: FakeStorage
):
    client.post(
        "/api/users/",
        json={
            **CONSENTS,
            "username": "alice",
            "avatarMode": "photo",
            "avatarUrl": _upload_avatar(fake_storage),
        },
    )

    response = client.patch("/api/users/current", json={"avatarMode": "animal"})

    assert response.status_code == 200
    body = response.json()
    assert body["avatarMode"] == "animal"
    assert body["avatarUrl"] == PERMANENT_AVATAR_URL


def test_create_user_fails_with_duplicate_username(client: TestClient, session: Session):
    _create_other_user(session, username="taken")

    response = client.post("/api/users/", json={**CONSENTS, "username": "taken"})

    assert response.status_code == 409


def test_create_user_fails_with_invalid_username_format(client: TestClient):
    response = client.post("/api/users/", json={**CONSENTS, "username": "a..b"})

    assert response.status_code == 422


def test_create_user_fails_with_too_long_bio(client: TestClient):
    response = client.post("/api/users/", json={**CONSENTS, "username": "alice", "bio": "x" * 151})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "avatar_url",
    [
        "https://evil.example/x.jpg",
        # someone else's pending upload
        f"{BASE_URL}/pending/avatars/auth0|someone-else/1.jpg",
        # already permanent, not from a fresh upload
        PERMANENT_AVATAR_URL,
        # nested below the user's own folder
        f"{BASE_URL}/pending/avatars/auth0|test-user/sub/1.jpg",
    ],
)
def test_create_user_fails_with_invalid_avatar_url(
    client: TestClient, fake_storage: FakeStorage, avatar_url: str
):
    # the object exists, so only the ownership/location check can reject it
    fake_storage.objects.add(avatar_url.removeprefix(f"{BASE_URL}/"))

    response = client.post("/api/users/", json={**CONSENTS, "username": "alice", "avatarUrl": avatar_url})

    assert response.status_code == 400
    assert fake_storage.deleted == []


def test_create_user_fails_when_pending_avatar_was_never_uploaded(client: TestClient):
    response = client.post(
        "/api/users/",
        json={**CONSENTS, "username": "alice", "avatarUrl": f"{BASE_URL}/pending/avatars/auth0|test-user/1.jpg"},
    )

    assert response.status_code == 400


def test_create_user_promotes_pending_avatar(client: TestClient, fake_storage: FakeStorage):
    response = client.post(
        "/api/users/", json={**CONSENTS, "username": "alice", "avatarUrl": _upload_avatar(fake_storage)}
    )

    assert response.status_code == 200
    assert response.json()["avatarUrl"] == PERMANENT_AVATAR_URL
    assert fake_storage.objects == {"avatars/auth0|test-user/1.jpg"}


def test_create_user_removes_promoted_copy_when_commit_fails(
    client: TestClient,
    session: Session,
    fake_storage: FakeStorage,
    monkeypatch: pytest.MonkeyPatch,
):
    # simulates a username race: the upfront check passes, the unique constraint then fails the commit
    _create_other_user(session, username="taken")
    monkeypatch.setattr(
        user_command_service.repository, "exists_by_username", lambda session, username: False
    )

    response = client.post(
        "/api/users/", json={**CONSENTS, "username": "taken", "avatarUrl": _upload_avatar(fake_storage)}
    )

    assert response.status_code == 409
    # pending original survives for a retry, the permanent copy is gone again
    assert fake_storage.objects == {"pending/avatars/auth0|test-user/1.jpg"}


def test_update_user_partial_update(client: TestClient):
    client.post("/api/users/", json={**CONSENTS, "username": "alice", "bio": "old"})

    response = client.patch("/api/users/current", json={"bio": "new"})

    assert response.status_code == 200
    body = response.json()
    assert body["bio"] == "new"
    assert body["username"] == "alice"


def test_update_user_clears_avatar_with_explicit_null(client: TestClient, fake_storage: FakeStorage):
    client.post("/api/users/", json={**CONSENTS, "username": "alice", "avatarUrl": _upload_avatar(fake_storage)})

    response = client.patch("/api/users/current", json={"avatarUrl": None})

    assert response.status_code == 200
    assert response.json()["avatarUrl"] is None
    assert fake_storage.objects == set()


def test_update_user_replaces_avatar_and_deletes_old_one(client: TestClient, fake_storage: FakeStorage):
    client.post("/api/users/", json={**CONSENTS, "username": "alice", "avatarUrl": _upload_avatar(fake_storage)})

    response = client.patch(
        "/api/users/current", json={"avatarUrl": _upload_avatar(fake_storage, "2.jpg")}
    )

    assert response.status_code == 200
    assert response.json()["avatarUrl"] == f"{BASE_URL}/avatars/auth0|test-user/2.jpg"
    assert fake_storage.objects == {"avatars/auth0|test-user/2.jpg"}


def test_update_user_with_unchanged_avatar_url_is_a_no_op(client: TestClient, fake_storage: FakeStorage):
    client.post("/api/users/", json={**CONSENTS, "username": "alice", "avatarUrl": _upload_avatar(fake_storage)})
    fake_storage.deleted.clear()

    response = client.patch(
        "/api/users/current", json={"username": "bob", "avatarUrl": PERMANENT_AVATAR_URL}
    )

    assert response.status_code == 200
    assert response.json()["avatarUrl"] == PERMANENT_AVATAR_URL
    assert fake_storage.deleted == []


def test_update_user_rejects_someone_elses_avatar(client: TestClient, fake_storage: FakeStorage):
    client.post("/api/users/", json={**CONSENTS, "username": "alice"})
    fake_storage.objects.add("avatars/auth0|someone-else/1.jpg")

    response = client.patch(
        "/api/users/current", json={"avatarUrl": f"{BASE_URL}/avatars/auth0|someone-else/1.jpg"}
    )

    assert response.status_code == 400


def test_update_user_fails_with_duplicate_username(client: TestClient, session: Session):
    _create_other_user(session, username="taken")
    client.post("/api/users/", json={**CONSENTS, "username": "alice"})

    response = client.patch("/api/users/current", json={"username": "taken"})

    assert response.status_code == 409


def test_avatar_upload_url_returns_presigned_url(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        storage,
        "generate_presigned_upload_url",
        lambda key, content_type: (
            f"https://upload.example/{key}",
            f"{BASE_URL}/{key}",
        ),
    )

    response = client.post("/api/users/current/avatar-upload-url", json={"contentType": "image/jpeg"})

    assert response.status_code == 200
    body = response.json()
    assert body["uploadUrl"].startswith("https://upload.example/pending/avatars/auth0|test-user/")
    assert body["avatarUrl"].startswith(f"{BASE_URL}/pending/avatars/auth0|test-user/")
    assert body["avatarUrl"].endswith(".jpg")


def test_avatar_upload_url_rejects_disallowed_content_type(client: TestClient):
    response = client.post("/api/users/current/avatar-upload-url", json={"contentType": "video/mp4"})

    assert response.status_code == 422


def test_username_availability(client: TestClient):
    response = client.get("/api/users/username-availability", params={"username": "alice"})
    assert response.json() == {"isAvailable": True}

    client.post("/api/users/", json={**CONSENTS, "username": "alice"})

    response = client.get("/api/users/username-availability", params={"username": "alice"})
    assert response.json() == {"isAvailable": False}


NEXT_TERMS_VERSION = "2027-01-01"


def _bump_current_terms_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "current_terms_version", NEXT_TERMS_VERSION)


def _terms_acceptance_count(session: Session) -> int:
    return len(session.exec(select(TermsAcceptance)).all())


@pytest.mark.parametrize("missing_field", ["crashReportsConsent", "acceptedTermsVersion"])
def test_create_user_requires_consents(client: TestClient, missing_field: str):
    body = {**CONSENTS, "username": "alice"}
    del body[missing_field]

    response = client.post("/api/users/", json=body)

    assert response.status_code == 422


def test_create_user_rejects_malformed_terms_version(client: TestClient):
    response = client.post(
        "/api/users/", json={**CONSENTS, "username": "alice", "acceptedTermsVersion": "01.11.2026"}
    )

    assert response.status_code == 422


def test_create_user_rejects_outdated_terms_version(client: TestClient):
    response = client.post(
        "/api/users/", json={**CONSENTS, "username": "alice", "acceptedTermsVersion": "2025-01-01"}
    )

    assert response.status_code == 400


def test_create_user_fails_when_terms_are_not_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(get_settings(), "current_terms_version", "")

    response = client.post("/api/users/", json={**CONSENTS, "username": "alice"})

    # a server misconfiguration, not the client's fault - so no 400
    assert response.status_code == 500


def test_create_user_stores_consents(client: TestClient):
    response = client.post(
        "/api/users/", json={**CONSENTS, "username": "alice", "crashReportsConsent": True}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["crashReportsConsent"] is True
    assert body["crashReportsConsentUpdatedAt"] is not None
    assert body["acceptedTermsVersion"] == CURRENT_TERMS_VERSION
    assert body["acceptedTermsAt"] is not None
    assert body["hasAcceptedCurrentTerms"] is True


def test_update_user_accepts_new_terms_version(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
):
    client.post("/api/users/", json={**CONSENTS, "username": "alice"})
    _bump_current_terms_version(monkeypatch)

    before = client.get("/api/users/current").json()
    response = client.patch("/api/users/current", json={"acceptedTermsVersion": NEXT_TERMS_VERSION})

    assert before["hasAcceptedCurrentTerms"] is False
    assert response.status_code == 200
    body = response.json()
    assert body["acceptedTermsVersion"] == NEXT_TERMS_VERSION
    assert body["hasAcceptedCurrentTerms"] is True
    # the old acceptance stays as history
    assert _terms_acceptance_count(session) == 2


def test_update_user_accepting_same_terms_version_again_is_a_no_op(client: TestClient, session: Session):
    client.post("/api/users/", json={**CONSENTS, "username": "alice"})

    response = client.patch("/api/users/current", json={"acceptedTermsVersion": CURRENT_TERMS_VERSION})

    assert response.status_code == 200
    assert _terms_acceptance_count(session) == 1


def test_update_user_rejects_outdated_terms_version(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    client.post("/api/users/", json={**CONSENTS, "username": "alice"})
    _bump_current_terms_version(monkeypatch)

    response = client.patch("/api/users/current", json={"acceptedTermsVersion": CURRENT_TERMS_VERSION})

    assert response.status_code == 400


def test_update_user_crash_reports_consent_only_touches_timestamp_on_change(client: TestClient):
    created = client.post("/api/users/", json={**CONSENTS, "username": "alice"}).json()

    changed = client.patch("/api/users/current", json={"crashReportsConsent": True}).json()
    unchanged = client.patch("/api/users/current", json={"crashReportsConsent": True}).json()

    assert changed["crashReportsConsent"] is True
    assert datetime.fromisoformat(changed["crashReportsConsentUpdatedAt"]) > datetime.fromisoformat(
        created["crashReportsConsentUpdatedAt"]
    )
    assert unchanged["crashReportsConsentUpdatedAt"] == changed["crashReportsConsentUpdatedAt"]


@pytest.mark.parametrize("field", ["crashReportsConsent", "acceptedTermsVersion"])
def test_update_user_rejects_explicit_null_for_consents(client: TestClient, field: str):
    client.post("/api/users/", json={**CONSENTS, "username": "alice"})

    response = client.patch("/api/users/current", json={field: None})

    assert response.status_code == 422
