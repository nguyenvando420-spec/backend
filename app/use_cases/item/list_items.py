from datetime import datetime
from typing import List, Optional
from app.domain.entities.item import Item
from app.domain.exceptions.item_exceptions import InvalidItemDataException
from app.use_cases.interfaces.item_repository import ItemRepository


class ListItemsUseCase:
    """Use case to list items with pagination and optional time range filtering."""

    def __init__(self, item_repository: ItemRepository):
        self.item_repository = item_repository

    async def execute(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Item]:
        if start_date and end_date and start_date > end_date:
            raise InvalidItemDataException("start_date cannot be greater than end_date.")

        return await self.item_repository.list_all(
            skip=skip,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )
