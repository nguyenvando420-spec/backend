from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.api.v1.schemas.item_schema import ItemCreateRequest, ItemResponse
from app.api.v1.dependencies import (
    get_create_item_use_case,
    get_get_item_use_case,
    get_list_items_use_case,
)
from app.use_cases.item.create_item import CreateItemUseCase
from app.use_cases.item.get_item import GetItemUseCase
from app.use_cases.item.list_items import ListItemsUseCase

router = APIRouter(prefix="/items", tags=["Items"])


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new item"
)
async def create_item(
    request: ItemCreateRequest,
    use_case: CreateItemUseCase = Depends(get_create_item_use_case),
):
    """Endpoint to create an item by dispatching to CreateItemUseCase."""
    item = await use_case.execute(
        title=request.title,
        price=request.price,
        description=request.description
    )
    return item


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Get item by ID"
)
async def get_item(
    item_id: str,
    use_case: GetItemUseCase = Depends(get_get_item_use_case),
):
    """Endpoint to get an item by ID by dispatching to GetItemUseCase."""
    item = await use_case.execute(item_id)
    return item


@router.get(
    "",
    response_model=List[ItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List items with pagination and time range filtering"
)
async def list_items(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of items to return"),
    start_date: Optional[datetime] = Query(
        None,
        description="Filter items created on or after this timestamp (e.g., 2026-01-01T00:00:00)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter items created on or before this timestamp (e.g., 2026-12-31T23:59:59)"
    ),
    use_case: ListItemsUseCase = Depends(get_list_items_use_case),
):
    """Endpoint to list items with optional date range filtering by dispatching to ListItemsUseCase."""
    items = await use_case.execute(
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date
    )
    return items
