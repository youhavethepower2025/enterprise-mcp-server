from __future__ import annotations

from app.mcp.base import BaseTool
from app.mcp.ecosystems.amazon.client import AmazonClient
from app.mcp.models import ToolMetadata, ToolResponse

DOCS_PREFIX = "Docs/amazon"


class AmazonOrderDigestTool(BaseTool):
    metadata = ToolMetadata(
        name="amazon.order_digest",
        description="Summarize the latest Amazon orders for fulfillment.",
        ecosystem="amazon",
        docs_path=f"{DOCS_PREFIX}/endpoints.md",
        requires_secrets=["AMAZON_REFRESH_TOKEN"],
    )

    def __init__(self, client: AmazonClient) -> None:
        super().__init__(client=client)

    def run(self) -> ToolResponse:
        orders = self.client.list_orders()
        return ToolResponse(status="ok", data={"orders": orders}, metadata={"source": "sample"})


class AmazonInventorySnapshotTool(BaseTool):
    metadata = ToolMetadata(
        name="amazon.inventory_snapshot",
        description="Capture inventory metrics derived from Amazon orders.",
        ecosystem="amazon",
        docs_path=f"{DOCS_PREFIX}/workflows.md",
        requires_secrets=["AMAZON_REFRESH_TOKEN"],
    )

    def __init__(self, client: AmazonClient) -> None:
        super().__init__(client=client)

    def run(self) -> ToolResponse:
        snapshot = self.client.inventory_snapshot()
        return ToolResponse(status="ok", data=snapshot, metadata={"source": "sample"})
