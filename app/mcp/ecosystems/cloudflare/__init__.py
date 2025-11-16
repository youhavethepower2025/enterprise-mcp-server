from __future__ import annotations

from typing import List

from app.mcp.ecosystems.cloudflare.client import CloudflareClient
from app.mcp.ecosystems.cloudflare.tools import (
    CloudflareDnsAuditTool,
    CloudflareDnsPreviewTool,
)


def build_tools() -> List[object]:
    client = CloudflareClient()
    return [
        CloudflareDnsAuditTool(client=client),
        CloudflareDnsPreviewTool(client=client),
    ]
