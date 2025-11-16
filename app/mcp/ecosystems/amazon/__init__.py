from __future__ import annotations

from typing import List

from app.mcp.ecosystems.amazon.client import AmazonClient
from app.mcp.ecosystems.amazon.tools import AmazonOrderDigestTool, AmazonInventorySnapshotTool


def build_tools() -> List[object]:
    client = AmazonClient()
    return [
        AmazonOrderDigestTool(client=client),
        AmazonInventorySnapshotTool(client=client),
    ]
