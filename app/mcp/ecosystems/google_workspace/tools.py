from __future__ import annotations

from app.mcp.base import BaseTool
from app.mcp.ecosystems.google_workspace.client import GoogleWorkspaceClient
from app.mcp.models import ToolMetadata, ToolResponse

DOCS_PREFIX = "Docs/google_workspace"


class GoogleWorkspaceDocCatalogTool(BaseTool):
    metadata = ToolMetadata(
        name="google_workspace.list_assets",
        description="List curated Docs and Sheets for MedTainer operations.",
        ecosystem="google_workspace",
        docs_path=f"{DOCS_PREFIX}/connections.md",
        requires_secrets=["GOOGLE_WORKSPACE_CREDENTIALS"],
    )

    def __init__(self, client: GoogleWorkspaceClient) -> None:
        super().__init__(client=client)

    def run(self) -> ToolResponse:
        assets = self.client.list_assets()
        source = "live" if self.client.credentials_path else "sample"
        return ToolResponse(status="ok", data=assets, metadata={"source": source})


class GoogleWorkspaceSheetSyncTool(BaseTool):
    metadata = ToolMetadata(
        name="google_workspace.sync_sheet",
        description="Push lead metrics into the pipeline Sheet for dashboards.",
        ecosystem="google_workspace",
        docs_path=f"{DOCS_PREFIX}/workflows.md",
        requires_secrets=["GOOGLE_WORKSPACE_CREDENTIALS"],
    )

    def __init__(self, client: GoogleWorkspaceClient) -> None:
        super().__init__(client=client)

    def run(self, sheet_id: str, rows: list[dict]) -> ToolResponse:
        result = self.client.sync_sheet(sheet_id, rows)
        return ToolResponse(status="ok", data={"result": result}, metadata={"sheet_id": sheet_id})
