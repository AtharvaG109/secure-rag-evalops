import pytest

from app.core.authz import NamespaceAuthz
from app.core.orm import NamespaceAccessORM


class FakeSession:
    def __init__(self, access: NamespaceAccessORM | None = None) -> None:
        self.access = access

    async def scalar(self, _: object) -> NamespaceAccessORM | None:
        return self.access


@pytest.mark.asyncio
async def test_demo_admin_always_passes() -> None:
    authz = NamespaceAuthz(FakeSession())  # type: ignore[arg-type]
    assert await authz.check_access("demo-admin", "any", "admin") is True


@pytest.mark.asyncio
async def test_unauthorized_user_is_denied() -> None:
    authz = NamespaceAuthz(FakeSession())  # type: ignore[arg-type]
    with pytest.raises(PermissionError, match="namespace_not_permitted"):
        await authz.require_read("analyst", "security-policy")
