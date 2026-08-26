import asyncio
import uuid
from datetime import datetime, timedelta
import random
import time

from sqlalchemy import insert, select, func
from app.infrastructure.database.connection import engine, AsyncSessionLocal, Base
from app.infrastructure.database.models.item_model import ItemModel


async def seed_large_dataset(total_records: int = 100_000, batch_size: int = 5_000):
    """Seed a large amount of items into PostgreSQL quickly using chunked batch inserts."""
    print(f"🚀 Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    start_time = time.perf_counter()
    print(f"📦 Generating and inserting {total_records:,} records in batches of {batch_size:,}...")

    base_time = datetime.utcnow()
    categories = ["Laptop", "Smartphone", "Monitor", "Keyboard", "Mouse", "Headphones", "Server", "Tablet", "Camera", "Watch"]

    async with AsyncSessionLocal() as session:
        # Check current count
        result = await session.execute(select(func.count(ItemModel.id)))
        current_count = result.scalar_one()
        print(f"ℹ️ Current records in database: {current_count:,}")

        if current_count >= total_records:
            print(f"✅ Database already has {current_count:,} records. Seeding skipped.")
            return

        records_to_insert = total_records - current_count
        inserted = 0

        for batch_start in range(0, records_to_insert, batch_size):
            current_batch_size = min(batch_size, records_to_insert - batch_start)
            batch = []

            for i in range(current_batch_size):
                idx = current_count + inserted + i + 1
                category = random.choice(categories)
                batch.append({
                    "id": str(uuid.uuid4()),
                    "title": f"{category} Model Pro-{idx}",
                    "description": f"High performance {category.lower()} with grade-A specifications, index #{idx}",
                    "price": round(random.uniform(50.0, 4999.0), 2),
                    "is_active": True,
                    "created_at": base_time - timedelta(minutes=random.randint(0, 525600)),
                })

            await session.execute(insert(ItemModel), batch)
            await session.commit()

            inserted += current_batch_size
            elapsed = time.perf_counter() - start_time
            print(f"  ⚡ Inserted {inserted:,}/{records_to_insert:,} records... ({elapsed:.2f}s, {inserted/elapsed:.0f} records/s)")

    total_time = time.perf_counter() - start_time
    print(f"🎉 Successfully seeded {total_records:,} items in {total_time:.2f} seconds ({total_records/total_time:.0f} rows/s)!")


if __name__ == "__main__":
    asyncio.run(seed_large_dataset(100_000))
