import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.common import storage
from app.users.application.command import user_command_service


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


def test_create_user_with_full_profile_fields(client: TestClient):
    response = client.post(
        "/api/users/",
        json={
            "username": "alice",
            "animalAssetName": "fox",
            "avatarColor": 3,
            "bioLine1": "Hello there",
            "bioLine2": "General Kenobi",
            "avatarUrl": "https://pub-test.example.r2.dev/avatars/x/1.jpg",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["animalAssetName"] == "fox"
    assert body["avatarColor"] == 3
    assert body["bioLine1"] == "Hello there"
    assert body["bioLine2"] == "General Kenobi"
    assert body["avatarUrl"] == "https://pub-test.example.r2.dev/avatars/x/1.jpg"


def test_create_user_fails_with_duplicate_username(client: TestClient, session: Session):
    user_command_service.create_user(session, username="taken", external_auth_id="auth0|someone-else")

    response = client.post("/api/users/", json={"username": "taken"})

    assert response.status_code == 409


def test_create_user_fails_with_invalid_username_format(client: TestClient):
    response = client.post("/api/users/", json={"username": "a..b"})

    assert response.status_code == 422


def test_create_user_fails_with_invalid_avatar_url(client: TestClient):
    response = client.post(
        "/api/users/", json={"username": "alice", "avatarUrl": "https://evil.example/x.jpg"}
    )

    assert response.status_code == 400


def test_update_user_partial_update(client: TestClient):
    client.post("/api/users/", json={"username": "alice", "bioLine1": "old"})

    response = client.patch("/api/users/current", json={"bioLine1": "new"})

    assert response.status_code == 200
    body = response.json()
    assert body["bioLine1"] == "new"
    assert body["username"] == "alice"


def test_update_user_clears_avatar_with_explicit_null(client: TestClient):
    client.post(
        "/api/users/",
        json={"username": "alice", "avatarUrl": "https://pub-test.example.r2.dev/avatars/x/1.jpg"},
    )

    response = client.patch("/api/users/current", json={"avatarUrl": None})

    assert response.status_code == 200
    assert response.json()["avatarUrl"] is None


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
            f"https://pub-test.example.r2.dev/{key}",
        ),
    )

    response = client.post("/api/users/current/avatar-upload-url", json={"contentType": "image/jpeg"})

    assert response.status_code == 200
    body = response.json()
    assert body["uploadUrl"].startswith("https://upload.example/avatars/auth0|test-user/")
    assert body["avatarUrl"].startswith("https://pub-test.example.r2.dev/avatars/auth0|test-user/")
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
