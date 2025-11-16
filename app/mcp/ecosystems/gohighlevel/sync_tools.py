"""GoHighLevel sync tools for MCP server.

These tools allow triggering syncs and checking sync status via the MCP interface.
"""

from app.mcp.base import BaseTool
from app.mcp.models import ToolMetadata, ToolResponse
from app.db.session import SessionLocal
from app.services.ghl_sync import GoHighLevelSyncService
import logging

logger = logging.getLogger(__name__)


class SyncAllContactsTool(BaseTool):
    """Sync all contacts from GoHighLevel into the central nervous system."""

    metadata = ToolMetadata(
        name="gohighlevel.sync_all_contacts",
        description=(
            "Pull ALL contacts from GoHighLevel and store in PostgreSQL. "
            "This creates the 'brain' - a complete copy of all contact data for fast access "
            "and intelligent search. Run this frequently to keep the nervous system in sync."
        ),
        ecosystem="gohighlevel",
        requires_secrets=["GOHIGHLEVEL_API_KEY"],
    )

    def __init__(self) -> None:
        super().__init__(client=None)  # No client needed, uses service

    def run(self, full_sync: bool = True) -> ToolResponse:
        """
        Execute the sync.

        Args:
            full_sync: If True, sync all contacts. If False, only recent updates.

        Returns:
            ToolResponse with sync statistics
        """
        logger.info("Starting GoHighLevel contact sync via MCP tool")

        db = SessionLocal()
        try:
            service = GoHighLevelSyncService(db)
            stats = service.sync_all_contacts(full_sync=full_sync)

            if stats.get("errors"):
                return ToolResponse(
                    status="partial",
                    data=stats,
                    metadata={
                        "source": "live",
                        "message": f"Sync completed with {len(stats['errors'])} errors",
                    },
                )

            return ToolResponse(
                status="ok",
                data=stats,
                metadata={
                    "source": "live",
                    "message": (
                        f"Synced {stats['contacts_fetched']} contacts: "
                        f"{stats['contacts_created']} created, {stats['contacts_updated']} updated"
                    ),
                },
            )

        except Exception as e:
            logger.error(f"Sync failed: {str(e)}", exc_info=True)
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "live"},
            )
        finally:
            db.close()


class GetSyncStatsTool(BaseTool):
    """Get statistics about the current sync state of the nervous system."""

    metadata = ToolMetadata(
        name="gohighlevel.get_sync_stats",
        description=(
            "Get statistics about the central nervous system's sync state: "
            "total contacts cached, last sync time, contact types, importance distribution. "
            "Use this to monitor the health of the nervous system."
        ),
        ecosystem="gohighlevel",
        requires_secrets=[],
    )

    def __init__(self) -> None:
        super().__init__(client=None)

    def run(self) -> ToolResponse:
        """Get sync statistics."""
        db = SessionLocal()
        try:
            service = GoHighLevelSyncService(db)
            stats = service.get_sync_stats()

            return ToolResponse(
                status="ok",
                data=stats,
                metadata={
                    "source": "database",
                    "message": f"Central nervous system has {stats['total_contacts']} contacts cached",
                },
            )

        except Exception as e:
            logger.error(f"Failed to get sync stats: {str(e)}", exc_info=True)
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "database"},
            )
        finally:
            db.close()
