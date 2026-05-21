from fastapi.testclient import TestClient

from app.core.dependencies import get_namespace_authz
from app.core.orm import ChunkORM, DocumentORM, EntityORM, EntityRelationORM
from app.main import app


class AllowAuthz:
    async def require_read(self, _: str, __: str) -> None:
        return None


class FakeSession:
    def __init__(self) -> None:
        self.calls = 0
        self.entities = [
            EntityORM(
                id="entity-1",
                namespace="real-docs",
                normalized_name="paymentservice",
                display_name="PaymentService",
                entity_type="concept",
            ),
            EntityORM(
                id="entity-2",
                namespace="real-docs",
                normalized_name="postgresql",
                display_name="PostgreSQL",
                entity_type="concept",
            ),
        ]
        self.relation = EntityRelationORM(
            id="relation-1",
            namespace="real-docs",
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            relation_type="uses",
            evidence_chunk_id="chunk-1",
            confidence=1.0,
        )
        self.chunk = ChunkORM(
            id="chunk-1",
            document_id="doc-1",
            text="PaymentService uses PostgreSQL.",
            chunk_index=0,
            token_count=4,
            page_start=1,
            page_end=1,
        )
        self.document = DocumentORM(
            id="doc-1",
            namespace="real-docs",
            source_type="md",
            source_filename="architecture.md",
            file_hash="hash",
            metadata_json={},
        )

    async def execute(self, _: object):
        self.calls += 1
        if self.calls == 1:
            return [(self.relation, self.chunk, self.document)]
        return [(self.entities[0], 3), (self.entities[1], 2)]


class FakeSearchSession(FakeSession):
    async def execute(self, _: object):
        self.calls += 1
        if self.calls == 1:
            return [(self.entities[0], 3)]
        if self.calls == 2:
            return [(self.relation, self.chunk, self.document)]
        return [(self.entities[0], 3), (self.entities[1], 2)]


class FakeNeighborhoodSession(FakeSession):
    async def execute(self, _: object):
        self.calls += 1
        if self.calls == 1:
            return [(self.relation, self.chunk, self.document)]
        return [(self.entities[0], 3), (self.entities[1], 2)]


def test_graph_api_returns_nodes_and_edges() -> None:
    from app.core.database import get_session

    session = FakeSession()
    app.dependency_overrides[get_namespace_authz] = lambda: AllowAuthz()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        response = client.get("/api/v1/graph?namespace=real-docs")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "nodes": [
            {
                "id": "entity-1",
                "label": "PaymentService",
                "entity_type": "concept",
                "mention_count": 3,
            },
            {
                "id": "entity-2",
                "label": "PostgreSQL",
                "entity_type": "concept",
                "mention_count": 2,
            },
        ],
        "edges": [
            {
                "id": "relation-1",
                "source": "entity-1",
                "target": "entity-2",
                "relation_type": "uses",
                "evidence_chunk_id": "chunk-1",
                "source_filename": "architecture.md",
                "snippet": "PaymentService uses PostgreSQL.",
                "confidence": 1.0,
            }
        ],
    }


def test_graph_api_expands_neighbors_for_search() -> None:
    from app.core.database import get_session

    session = FakeSearchSession()
    app.dependency_overrides[get_namespace_authz] = lambda: AllowAuthz()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        response = client.get("/api/v1/graph?namespace=real-docs&search=Payment")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert {node["label"] for node in response.json()["nodes"]} == {
        "PaymentService",
        "PostgreSQL",
    }
    assert response.json()["edges"][0]["relation_type"] == "uses"


def test_graph_api_expands_neighbors_for_entity() -> None:
    from app.core.database import get_session

    session = FakeNeighborhoodSession()
    app.dependency_overrides[get_namespace_authz] = lambda: AllowAuthz()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        response = client.get("/api/v1/graph?namespace=real-docs&entity_id=entity-1")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert {node["id"] for node in response.json()["nodes"]} == {"entity-1", "entity-2"}
    assert response.json()["edges"][0]["id"] == "relation-1"


def test_graph_api_rejects_unbounded_limits() -> None:
    from app.core.database import get_session

    app.dependency_overrides[get_namespace_authz] = lambda: AllowAuthz()
    app.dependency_overrides[get_session] = lambda: FakeSession()
    with TestClient(app) as client:
        response = client.get("/api/v1/graph?namespace=real-docs&limit=0")
    app.dependency_overrides.clear()

    assert response.status_code == 422
