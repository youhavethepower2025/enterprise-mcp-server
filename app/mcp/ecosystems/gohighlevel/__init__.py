from __future__ import annotations

from typing import List

from app.mcp.ecosystems.gohighlevel.client import GoHighLevelClient
from app.mcp.ecosystems.gohighlevel.tools import (
    GoHighLevelContactSnapshotTool,
    GoHighLevelPipelineDigestTool,
)
from app.mcp.ecosystems.gohighlevel.sync_tools import (
    SyncAllContactsTool,
    GetSyncStatsTool,
)
from app.mcp.ecosystems.gohighlevel.intelligence_tools import (
    GetActionableInsightsTool,
    AnalyzeContactTool,
    GetContactRecommendationsTool,
)
from app.mcp.ecosystems.gohighlevel.action_tools import (
    CreateContactTool,
    UpdateContactTool,
    SendSMSTool,
    AddNoteTool,
    AddTagsTool,
    RemoveTagsTool,
)


def build_tools() -> List[object]:
    client = GoHighLevelClient()
    return [
        # Basic read tools
        GoHighLevelContactSnapshotTool(client=client),
        GoHighLevelPipelineDigestTool(client=client),
        # Sync tools - for building the central nervous system
        SyncAllContactsTool(),
        GetSyncStatsTool(),
        # Agentic intelligence tools - semi-autonomous reasoning
        GetActionableInsightsTool(),
        AnalyzeContactTool(),
        GetContactRecommendationsTool(),
        # Action/write tools - enable the agent to take action
        CreateContactTool(client=client),
        UpdateContactTool(client=client),
        SendSMSTool(client=client),
        AddNoteTool(client=client),
        AddTagsTool(client=client),
        RemoveTagsTool(client=client),
    ]
