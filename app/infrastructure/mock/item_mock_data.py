from datetime import datetime, timedelta
from app.domain.entities.item import Item

# Danh sách dữ liệu mẫu (Mockup Data) cho tầng Infrastructure
MOCK_ITEMS = [
    Item(
        id="mock-item-uuid-101",
        title="MacBook Pro M3 Max",
        description="Laptop cao cấp dành cho Developers",
        price=3499.99,
        is_active=True,
        created_at=datetime.utcnow() - timedelta(days=5)
    ),
    Item(
        id="mock-item-uuid-102",
        title="iPhone 16 Pro",
        description="Điện thoại flagship mới nhất",
        price=1199.00,
        is_active=True,
        created_at=datetime.utcnow() - timedelta(days=3)
    ),
    Item(
        id="mock-item-uuid-103",
        title="Bàn phím cơ Keychron K2",
        description="Bàn phím không dây gõ phím êm ái",
        price=99.50,
        is_active=True,
        created_at=datetime.utcnow() - timedelta(days=1)
    ),
]
