import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.common import storage
from app.users.application.command import user_command_service
from tests.conftest import FakeStorage

BASE_URL = "https://pub-test.example.r2.dev"
PERMANENT_AVATAR_URL = f"{BASE_URL}/avatars/auth0|test-user/1.jpg"


def _upload_avatar(fake_storage: FakeStorage, file_name: str = "1.jpg") -> str:
    """Simulates a finished client upload - returns the pending URL the app would send."""
    key = f"pending/avatars/auth0|test-user/{file_name}"
    fake_storage.objects.add(key)
    return f"{BASE_URL}/{key}"


def test_create_and_get_current_user(client: TestClient):
    create_response = client.post("/api/users/", json={"username": "alice"})
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
    response = client.post("/api/users/", json={"username": "alice"})

    assert response.status_code == 200
    assert response.json()["avatarMode"] == "animal"


def test_create_user_with_photo_mode_and_avatar_url_succeeds(
    client: TestClient, fake_storage: FakeStorage
):
    response = client.post(
        "/api/users/",
        json={
            "username": "alice",
            "avatarMode": "photo",
            "avatarUrl": _upload_avatar(fake_storage),
        },
    )

    assert response.status_code == 200
    assert response.json()["avatarMode"] == "photo"


def test_create_user_fails_with_photo_mode_and_no_avatar_url(client: TestClient):
    response = client.post("/api/users/", json={"username": "alice", "avatarMode": "photo"})

    assert response.status_code == 400


def test_update_user_fails_switching_to_photo_mode_without_avatar_url(client: TestClient):
    client.post("/api/users/", json={"username": "alice"})

    response = client.patch("/api/users/current", json={"avatarMode": "photo"})

    assert response.status_code == 400


def test_update_user_switching_to_animal_mode_keeps_avatar_url(
    client: TestClient, fake_storage: FakeStorage
):
    client.post(
        "/api/users/",
        json={
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
    user_command_service.create_user(session, username="taken", external_auth_id="auth0|someone-else")

    response = client.post("/api/users/", json={"username": "taken"})

    assert response.status_code == 409


def test_create_user_fails_with_invalid_username_format(client: TestClient):
    response = client.post("/api/users/", json={"username": "a..b"})

    assert response.status_code == 422


def test_create_user_fails_with_too_long_bio(client: TestClient):
    response = client.post("/api/users/", json={"username": "alice", "bio": "x" * 151})

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

    response = client.post("/api/users/", json={"username": "alice", "avatarUrl": avatar_url})

    assert response.status_code == 400
    assert fake_storage.deleted == []


def test_create_user_fails_when_pending_avatar_was_never_uploaded(client: TestClient):
    response = client.post(
        "/api/users/",
        json={"username": "alice", "avatarUrl": f"{BASE_URL}/pending/avatars/auth0|test-user/1.jpg"},
    )

    assert response.status_code == 400


def test_create_user_promotes_pending_avatar(client: TestClient, fake_storage: FakeStorage):
    response = client.post(
        "/api/users/", json={"username": "alice", "avatarUrl": _upload_avatar(fake_storage)}
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
    user_command_service.create_user(session, username="taken", external_auth_id="auth0|someone-else")
    monkeypatch.setattr(
        user_command_service.repository, "exists_by_username", lambda session, username: False
    )

    response = client.post(
        "/api/users/", json={"username": "taken", "avatarUrl": _upload_avatar(fake_storage)}
    )

    assert response.status_code == 409
    # pending original survives for a retry, the permanent copy is gone again
    assert fake_storage.objects == {"pending/avatars/auth0|test-user/1.jpg"}


def test_update_user_partial_update(client: TestClient):
    client.post("/api/users/", json={"username": "alice", "bio": "old"})

    response = client.patch("/api/users/current", json={"bio": "new"})

    assert response.status_code == 200
    body = response.json()
    assert body["bio"] == "new"
    assert body["username"] == "alice"


def test_update_user_clears_avatar_with_explicit_null(client: TestClient, fake_storage: FakeStorage):
    client.post("/api/users/", json={"username": "alice", "avatarUrl": _upload_avatar(fake_storage)})

    response = client.patch("/api/users/current", json={"avatarUrl": None})

    assert response.status_code == 200
    assert response.json()["avatarUrl"] is None
    assert fake_storage.objects == set()


def test_update_user_replaces_avatar_and_deletes_old_one(client: TestClient, fake_storage: FakeStorage):
    client.post("/api/users/", json={"username": "alice", "avatarUrl": _upload_avatar(fake_storage)})

    response = client.patch(
        "/api/users/current", json={"avatarUrl": _upload_avatar(fake_storage, "2.jpg")}
    )

    assert response.status_code == 200
    assert response.json()["avatarUrl"] == f"{BASE_URL}/avatars/auth0|test-user/2.jpg"
    assert fake_storage.objects == {"avatars/auth0|test-user/2.jpg"}


def test_update_user_with_unchanged_avatar_url_is_a_no_op(client: TestClient, fake_storage: FakeStorage):
    client.post("/api/users/", json={"username": "alice", "avatarUrl": _upload_avatar(fake_storage)})
    fake_storage.deleted.clear()

    response = client.patch(
        "/api/users/current", json={"username": "bob", "avatarUrl": PERMANENT_AVATAR_URL}
    )

    assert response.status_code == 200
    assert response.json()["avatarUrl"] == PERMANENT_AVATAR_URL
    assert fake_storage.deleted == []


def test_update_user_rejects_someone_elses_avatar(client: TestClient, fake_storage: FakeStorage):
    client.post("/api/users/", json={"username": "alice"})
    fake_storage.objects.add("avatars/auth0|someone-else/1.jpg")

    response = client.patch(
        "/api/users/current", json={"avatarUrl": f"{BASE_URL}/avatars/auth0|someone-else/1.jpg"}
    )

    assert response.status_code == 400


def test_update_user_fails_with_duplicate_username(client: TestClient, session: Session):
    user_command_service.create_user(session, username="taken", external_auth_id="auth0|someone-else")
    client.post("/api/users/", json={"username": "alice"})

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

    client.post("/api/users/", json={"username": "alice"})

    response = client.get("/api/users/username-availability", params={"username": "alice"})
    assert response.json() == {"isAvailable": False}
