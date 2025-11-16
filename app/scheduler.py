"""
Task scheduler for MedTainer MCP.

Manages periodic background tasks including:
- Weekly GoDaddy cloud environment sync
- Other scheduled maintenance tasks
"""

from __future__ import annotations

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from app.services import run_weekly_sync, run_ghl_sync

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    """
    Start the background scheduler for periodic tasks.

    This should be called on application startup.
    """
    global scheduler

    if scheduler is not None and scheduler.running:
        logger.warning("Scheduler is already running")
        return

    scheduler = BackgroundScheduler(timezone='UTC')

    # Schedule weekly GoDaddy sync - runs every Sunday at 2:00 AM UTC
    scheduler.add_job(
        func=run_weekly_sync,
        trigger=CronTrigger(day_of_week='sun', hour=2, minute=0),
        id='godaddy_weekly_sync',
        name='GoDaddy Weekly Cloud Environment Sync',
        replace_existing=True,
        max_instances=1,  # Only one sync at a time
        misfire_grace_time=3600  # Allow 1 hour grace period if missed
    )

    # Schedule GoHighLevel contact sync - runs every 15 minutes
    # This keeps the central nervous system up-to-date with CRM changes
    scheduler.add_job(
        func=run_ghl_sync,
        trigger=IntervalTrigger(minutes=15),
        id='ghl_contact_sync',
        name='GoHighLevel Contact Sync (Every 15 Minutes)',
        replace_existing=True,
        max_instances=1,  # Prevent overlapping syncs
        misfire_grace_time=300  # Allow 5 minute grace period if missed
    )

    # Optional: Add daily health check sync (useful during testing/development)
    # Uncomment to enable daily syncs at 3:00 AM UTC
    # scheduler.add_job(
    #     func=run_weekly_sync,
    #     trigger=CronTrigger(hour=3, minute=0),
    #     id='godaddy_daily_sync',
    #     name='GoDaddy Daily Health Check Sync',
    #     replace_existing=True,
    #     max_instances=1
    # )

    scheduler.start()
    logger.info("Scheduler started successfully")
    logger.info(f"Next GoDaddy sync scheduled for: {scheduler.get_job('godaddy_weekly_sync').next_run_time}")
    logger.info(f"Next GoHighLevel sync scheduled for: {scheduler.get_job('ghl_contact_sync').next_run_time}")


def stop_scheduler() -> None:
    """
    Stop the background scheduler.

    This should be called on application shutdown.
    """
    global scheduler

    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped successfully")


def trigger_sync_now() -> None:
    """
    Manually trigger a GoDaddy sync immediately.

    Useful for testing or on-demand updates.
    """
    global scheduler

    if scheduler is None or not scheduler.running:
        logger.error("Scheduler is not running, cannot trigger sync")
        return

    scheduler.add_job(
        func=run_weekly_sync,
        trigger='date',  # Run once immediately
        id='godaddy_manual_sync',
        name='GoDaddy Manual Sync (Triggered)',
        replace_existing=True
    )
    logger.info("Manual GoDaddy sync triggered")


def get_scheduler_status() -> dict:
    """
    Get the current status of scheduled jobs.

    Returns:
        Dictionary with scheduler status and job information
    """
    global scheduler

    if scheduler is None or not scheduler.running:
        return {
            'running': False,
            'jobs': []
        }

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger)
        })

    return {
        'running': True,
        'jobs': jobs
    }
