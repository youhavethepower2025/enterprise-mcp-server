from __future__ import annotations

from app.mcp.base import BaseTool
from app.mcp.ecosystems.gohighlevel.client import GoHighLevelClient
from app.mcp.models import ToolMetadata, ToolResponse

DOCS_PREFIX = "Docs/gohighlevel"


class GoHighLevelContactSnapshotTool(BaseTool):
    metadata = ToolMetadata(
        name="gohighlevel.read_contacts",
        description="Return a snapshot of the freshest contacts and their pipeline stages.",
        ecosystem="gohighlevel",
        docs_path=f"{DOCS_PREFIX}/endpoints.md",
        requires_secrets=["GOHIGHLEVEL_API_KEY"],
    )

    def __init__(self, client: GoHighLevelClient) -> None:
        super().__init__(client=client)

    def run(self, limit: int = 10) -> ToolResponse:
        contacts = self.client.list_contacts(limit=limit)
        source = "live" if self.client.api_key else "sample"
        return ToolResponse(status="ok", data={"contacts": contacts}, metadata={"source": source})


class GoHighLevelPipelineDigestTool(BaseTool):
    metadata = ToolMetadata(
        name="gohighlevel.pipeline_digest",
        description="Aggregate pipeline counts by stage for executive reporting.",
        ecosystem="gohighlevel",
        docs_path=f"{DOCS_PREFIX}/workflows.md",
        requires_secrets=["GOHIGHLEVEL_API_KEY"],
    )

    def __init__(self, client: GoHighLevelClient) -> None:
        super().__init__(client=client)

    def run(self) -> ToolResponse:
        digest = self.client.pipeline_digest()
        source = "live" if self.client.api_key else "sample"
        return ToolResponse(status="ok", data={"pipeline": digest}, metadata={"source": source})
