from __future__ import annotations

from app.core.config import settings
from app.mcp.common.mock_data import sample_google_assets


class GoogleWorkspaceClient:
    """Placeholder client that will eventually wrap Google APIs via service accounts."""

    def __init__(self) -> None:
        self.project_id = settings.google_workspace_project_id
        self.credentials_path = settings.google_workspace_credentials_path

    def list_assets(self) -> dict:
        return sample_google_assets()

    def sync_sheet(self, sheet_id: str, rows: list[dict]) -> dict:
        if not self.credentials_path:
            return {"status": "pending_credentials", "sheet_id": sheet_id, "rows": rows}
        return {"status": "mock_synced", "sheet_id": sheet_id, "rows": rows}
