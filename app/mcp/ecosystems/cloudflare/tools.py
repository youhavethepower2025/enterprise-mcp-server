from __future__ import annotations

from app.mcp.base import BaseTool
from app.mcp.ecosystems.cloudflare.client import CloudflareClient
from app.mcp.models import ToolMetadata, ToolResponse

DOCS_PREFIX = "Docs/cloudflare"


class CloudflareDnsPreviewTool(BaseTool):
    metadata = ToolMetadata(
        name="cloudflare.list_dns",
        description="Preview DNS records to validate MCP-managed domains.",
        ecosystem="cloudflare",
        docs_path=f"{DOCS_PREFIX}/connections.md",
        requires_secrets=["CLOUDFLARE_API_TOKEN"],
    )

    def __init__(self, client: CloudflareClient) -> None:
        super().__init__(client=client)

    def run(self) -> ToolResponse:
        records = self.client.list_dns_records()
        return ToolResponse(status="ok", data={"records": records}, metadata={"source": "sample"})


class CloudflareDnsAuditTool(BaseTool):
    metadata = ToolMetadata(
        name="cloudflare.dns_audit",
        description="Highlight DNS entries that must exist for email + MCP routing.",
        ecosystem="cloudflare",
        docs_path=f"{DOCS_PREFIX}/monitoring.md",
        requires_secrets=["CLOUDFLARE_API_TOKEN"],
    )

    def __init__(self, client: CloudflareClient) -> None:
        super().__init__(client=client)

    def run(self) -> ToolResponse:
        audit = self.client.plan_audit()
        return ToolResponse(status="ok", data=audit, metadata={"account_id": self.client.account_id})
