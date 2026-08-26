from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.item import Item
from app.use_cases.interfaces.item_repository import ItemRepository
from app.infrastructure.database.models.item_model import ItemModel


class ItemRepositoryImpl(ItemRepository):
    """
    SQLAlchemy implementation of the ItemRepository interface.
    Handles data mapping between Domain Entities and ORM Models.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, item: Item) -> Item:
        db_item = ItemModel.from_entity(item)
        self.session.add(db_item)
        await self.session.flush()
        return db_item.to_entity()

    async def get_by_id(self, item_id: str) -> Optional[Item]:
        stmt = select(ItemModel).where(ItemModel.id == item_id)
        result = await self.session.execute(stmt)
        db_item = result.scalar_one_or_none()
        return db_item.to_entity() if db_item else None

    async def get_by_title(self, title: str) -> Optional[Item]:
        stmt = select(ItemModel).where(ItemModel.title == title)
        result = await self.session.execute(stmt)
        db_item = result.scalar_one_or_none()
        return db_item.to_entity() if db_item else None

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Item]:
        stmt = select(ItemModel)
        if start_date:
            stmt = stmt.where(ItemModel.created_at >= start_date)
        if end_date:
            stmt = stmt.where(ItemModel.created_at <= end_date)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        db_items = result.scalars().all()
        return [item.to_entity() for item in db_items]

    async def update(self, item: Item) -> Item:
        stmt = select(ItemModel).where(ItemModel.id == item.id)
        result = await self.session.execute(stmt)
        db_item = result.scalar_one_or_none()
        if db_item:
            db_item.title = item.title
            db_item.description = item.description
            db_item.price = item.price
            db_item.is_active = item.is_active
            await self.session.flush()
            return db_item.to_entity()
        return await self.create(item)

    async def delete(self, item_id: str) -> bool:
        stmt = select(ItemModel).where(ItemModel.id == item_id)
        result = await self.session.execute(stmt)
        db_item = result.scalar_one_or_none()
        if db_item:
            await self.session.delete(db_item)
            await self.session.flush()
            return True
        return False
