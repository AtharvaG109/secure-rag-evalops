from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.core.settings import settings
from app.main import app


class FakeRedis:
    async def incr(self, _: str) -> int:
        return 1

    async def expire(self, _: str, __: int) -> None:
        return None

    async def aclose(self) -> None:
        return None


def test_local_auth_me_uses_dev_identity() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "demo-admin",
        "is_superuser": True,
        "auth_method": "local_dev",
    }


def test_production_requires_authentication(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "ALLOW_LOCAL_DEV_AUTH", False)
    monkeypatch.setattr(settings, "AUTH_TOKEN_PEPPER", "secure-pepper")
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 120)
    monkeypatch.setattr(settings, "TRUSTED_HOSTS", "testserver")
    monkeypatch.setattr("app.core.security.Redis.from_url", lambda *_, **__: FakeRedis())
    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "authentication_required"
