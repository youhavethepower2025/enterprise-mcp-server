from __future__ import annotations

from typing import List

from app.mcp.ecosystems.google_workspace.client import GoogleWorkspaceClient
from app.mcp.ecosystems.google_workspace.tools import (
    GoogleWorkspaceDocCatalogTool,
    GoogleWorkspaceSheetSyncTool,
)


def build_tools() -> List[object]:
    client = GoogleWorkspaceClient()
    return [
        GoogleWorkspaceDocCatalogTool(client=client),
        GoogleWorkspaceSheetSyncTool(client=client),
    ]
