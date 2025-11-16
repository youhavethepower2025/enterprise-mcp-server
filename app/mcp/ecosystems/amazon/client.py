from __future__ import annotations

from app.core.config import settings
from app.mcp.common.mock_data import sample_amazon_orders


class AmazonClient:
    def __init__(self) -> None:
        self.refresh_token = settings.amazon_refresh_token

    def list_orders(self) -> list[dict]:
        return sample_amazon_orders()

    def inventory_snapshot(self) -> dict:
        orders = self.list_orders()
        total_items = sum(order["items"] for order in orders)
        return {"total_units": total_items, "orders_count": len(orders)}
