import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.infrastructure.database.connection import engine, Base


@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    """Ensure database tables are initialized and cleaned before tests run."""
    import app.infrastructure.database.models.item_model  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_create_and_get_item_api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create item
        create_payload = {
            "title": "MacBook Pro",
            "description": "Apple M3 Max",
            "price": 3499.99
        }
        res_create = await ac.post("/api/v1/items", json=create_payload)
        assert res_create.status_code == 201
        data = res_create.json()
        assert data["title"] == "MacBook Pro"
        assert data["price"] == 3499.99
        item_id = data["id"]

        # Get item by ID
        res_get = await ac.get(f"/api/v1/items/{item_id}")
        assert res_get.status_code == 200
        assert res_get.json()["id"] == item_id

        # List items
        res_list = await ac.get("/api/v1/items")
        assert res_list.status_code == 200
        assert len(res_list.json()) >= 1


@pytest.mark.asyncio
async def test_get_nonexistent_item_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/items/invalid-uuid-123")
        assert res.status_code == 404
        assert res.json()["code"] == "ITEM_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_items_date_filter():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/items", json={"title": "Item A", "price": 10})
        await ac.post("/api/v1/items", json={"title": "Item B", "price": 20})

        # Query with future start_date -> 0 results
        res_future = await ac.get("/api/v1/items?start_date=2099-01-01T00:00:00")
        assert res_future.status_code == 200
        assert len(res_future.json()) == 0

        # Query with past start_date -> returns created items
        res_past = await ac.get("/api/v1/items?start_date=2020-01-01T00:00:00")
        assert res_past.status_code == 200
        assert len(res_past.json()) >= 2
