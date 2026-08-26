from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.repositories.item_repository_impl import ItemRepositoryImpl
from app.infrastructure.repositories.in_memory_item_repository import get_in_memory_item_repository
from app.use_cases.interfaces.item_repository import ItemRepository
from app.use_cases.item.create_item import CreateItemUseCase
from app.use_cases.item.get_item import GetItemUseCase
from app.use_cases.item.list_items import ListItemsUseCase


def get_item_repository(session: AsyncSession = Depends(get_db_session)) -> ItemRepository:
    """
    Inject ItemRepository implementation.
    If USE_MOCK_DB=true, returns InMemoryItemRepository (with mockup data, no DB required).
    Otherwise returns ItemRepositoryImpl (SQLAlchemy DB connection).
    """
    if settings.USE_MOCK_DB:
        return get_in_memory_item_repository()
    return ItemRepositoryImpl(session)


def get_create_item_use_case(
    repo: ItemRepository = Depends(get_item_repository)
) -> CreateItemUseCase:
    """Inject CreateItemUseCase."""
    return CreateItemUseCase(repo)


def get_get_item_use_case(
    repo: ItemRepository = Depends(get_item_repository)
) -> GetItemUseCase:
    """Inject GetItemUseCase."""
    return GetItemUseCase(repo)


def get_list_items_use_case(
    repo: ItemRepository = Depends(get_item_repository)
) -> ListItemsUseCase:
    """Inject ListItemsUseCase."""
    return ListItemsUseCase(repo)
