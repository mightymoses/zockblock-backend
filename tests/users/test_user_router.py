from fastapi.testclient import TestClient


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
