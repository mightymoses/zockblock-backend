import pytest
from fastapi.testclient import TestClient
from app.config import get_settings
from app.main import app
from tests.conftest import CURRENT_TERMS_URL, CURRENT_TERMS_VERSION


def test_current_terms_are_public():
    # plain client on purpose: no auth override, no DB - the endpoint needs neither
    response = TestClient(app).get("/api/terms/current")

    assert response.status_code == 200
    assert response.json() == {"version": CURRENT_TERMS_VERSION, "url": CURRENT_TERMS_URL}


@pytest.mark.parametrize("setting", ["current_terms_version", "current_terms_url"])
def test_current_terms_fail_loudly_when_not_configured(monkeypatch: pytest.MonkeyPatch, setting: str):
    monkeypatch.setattr(get_settings(), setting, "")

    response = TestClient(app).get("/api/terms/current")

    assert response.status_code == 500
