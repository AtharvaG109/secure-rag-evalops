from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.dependencies import get_namespace_authz, get_vector_store
from app.core.orm import CollectionORM, DocumentORM
from app.main import app


class AllowAuthz:
    async def require_read(self, _: str, __: str) -> None:
        return None

    async def require_write(self, _: str, __: str) -> None:
        return None


class FakeSession:
    def __init__(self) -> None:
        self.collection = CollectionORM(
            id="collection-1",
            namespace="real-docs",
            name="default",
        )
        self.document = DocumentORM(
            id="doc-1",
            namespace="real-docs",
            source_type="py",
            source_filename="sample.py",
            file_hash="hash",
            metadata_json={},
            created_at=datetime(2026, 5, 1, tzinfo=UTC),
        )
        self.deleted = False
        self.deleted_rows: list[str] = []
        self.added: list[object] = []

    async def execute(self, _: object) -> list[tuple[DocumentORM, CollectionORM, int]]:
        return [(self.document, self.collection, 2)]

    async def scalar(self, _: object) -> DocumentORM:
        return self.document

    async def scalars(self, _: object) -> list[DocumentORM]:
        return [self.document]

    async def delete(self, _: object) -> None:
        self.deleted = True
        self.deleted_rows.append(self.document.id)

    def add(self, item: object) -> None:
        self.added.append(item)

    async def commit(self) -> None:
        return None


class FakeVectorStore:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete_document(self, document_id: str) -> None:
        self.deleted.append(document_id)


def test_list_documents() -> None:
    from app.core.database import get_session

    session = FakeSession()
    app.dependency_overrides[get_namespace_authz] = lambda: AllowAuthz()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        response = client.get("/api/v1/documents?namespace=real-docs&user_id=demo-admin")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["source_filename"] == "sample.py"
    assert response.json()[0]["collection_name"] == "default"
    assert response.json()[0]["chunk_count"] == 2
    assert response.json()[0]["created_at"] == "2026-05-01T00:00:00+00:00"


def test_delete_document_removes_vector_and_row() -> None:
    from app.core.database import get_session

    session = FakeSession()
    vector_store = FakeVectorStore()
    app.dependency_overrides[get_namespace_authz] = lambda: AllowAuthz()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_vector_store] = lambda: vector_store
    with TestClient(app) as client:
        response = client.delete("/api/v1/documents/doc-1?user_id=demo-admin")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert vector_store.deleted == ["doc-1"]
    assert session.deleted is True
    assert len(session.added) == 1


def test_cleanup_documents_deletes_collection_documents() -> None:
    from app.core.database import get_session

    session = FakeSession()
    vector_store = FakeVectorStore()
    app.dependency_overrides[get_namespace_authz] = lambda: AllowAuthz()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_vector_store] = lambda: vector_store
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents/cleanup",
            json={
                "namespace": "real-docs",
                "user_id": "demo-admin",
                "collection_name": "default",
                "dry_run": False,
                "confirm": True,
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "deleted_documents": 1,
        "matched_documents": 1,
        "dry_run": False,
    }
    assert vector_store.deleted == ["doc-1"]
    assert session.deleted_rows == ["doc-1"]
    assert len(session.added) == 1


def test_cleanup_documents_requires_filter() -> None:
    from app.core.database import get_session

    session = FakeSession()
    app.dependency_overrides[get_namespace_authz] = lambda: AllowAuthz()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents/cleanup",
            json={"namespace": "real-docs", "user_id": "demo-admin"},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "collection_name_or_older_than_days_required"


def test_cleanup_documents_previews_before_delete() -> None:
    from app.core.database import get_session

    session = FakeSession()
    vector_store = FakeVectorStore()
    app.dependency_overrides[get_namespace_authz] = lambda: AllowAuthz()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_vector_store] = lambda: vector_store
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents/cleanup",
            json={
                "namespace": "real-docs",
                "collection_name": "default",
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "deleted_documents": 0,
        "matched_documents": 1,
        "dry_run": True,
    }
    assert vector_store.deleted == []
