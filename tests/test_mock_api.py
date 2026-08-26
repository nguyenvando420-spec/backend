import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_mock_repository_api():
    # Force Mock DB mode
    original_setting = settings.USE_MOCK_DB
    settings.USE_MOCK_DB = True

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Fetch pre-seeded mock items
            res = await ac.get("/api/v1/items")
            assert res.status_code == 200
            items = res.json()
            assert len(items) >= 3
            assert items[0]["title"] == "MacBook Pro M3 Max"
            assert items[1]["title"] == "iPhone 16 Pro"

            # 2. Fetch specific pre-seeded mock item by ID
            res_item = await ac.get("/api/v1/items/mock-item-uuid-101")
            assert res_item.status_code == 200
            assert res_item.json()["title"] == "MacBook Pro M3 Max"

            # 3. Filter mock items by date range
            res_future = await ac.get("/api/v1/items?start_date=2099-01-01T00:00:00")
            assert res_future.status_code == 200
            assert len(res_future.json()) == 0

    finally:
        settings.USE_MOCK_DB = original_setting
