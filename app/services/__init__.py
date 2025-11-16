"""
Services module for MedTainer MCP.

Contains business logic services including:
- GoDaddy sync service for weekly cloud environment updates
- GoHighLevel sync service for frequent contact/CRM updates
"""

import logging
from typing import Dict, Any

from app.services.godaddy_sync import GoDaddySyncService, run_weekly_sync
from app.services.ghl_sync import GoHighLevelSyncService
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

__all__ = ['GoDaddySyncService', 'run_weekly_sync', 'GoHighLevelSyncService', 'run_ghl_sync']


def run_ghl_sync() -> Dict[str, Any]:
    """
    Convenience function to run GoHighLevel contact sync.

    This should be called by the scheduler every 15 minutes to keep
    the central nervous system up-to-date with the latest CRM data.

    Returns:
        Dictionary with sync statistics
    """
    logger.info("Starting scheduled GoHighLevel contact sync")
    db = SessionLocal()
    try:
        service = GoHighLevelSyncService(db)
        stats = service.sync_all_contacts(full_sync=True)
        logger.info(
            f"GoHighLevel sync completed: {stats['contacts_fetched']} fetched, "
            f"{stats['contacts_created']} created, {stats['contacts_updated']} updated"
        )
        return stats
    except Exception as e:
        logger.error(f"GoHighLevel sync failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
