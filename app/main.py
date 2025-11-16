from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.routes import router
from app.core import logging as _logging  # noqa: F401  # ensure loggers configure on import
from app.core.config import settings
from app.db.middleware import ToolLoggingMiddleware
from app.db.models import Base
from app.db.session import engine
from app.scheduler import start_scheduler, stop_scheduler
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    This runs on startup and shutdown of the FastAPI application.
    - On startup: Create database tables and start background scheduler
    - On shutdown: Stop scheduler and cleanup
    """
    # Startup: Create database tables
    logger.info("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}", exc_info=True)
        raise

    # Startup: Start background scheduler for weekly GoDaddy sync
    logger.info("Starting background scheduler...")
    try:
        start_scheduler()
        logger.info("Background scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        # Don't raise - scheduler is not critical for basic operation

    yield

    # Shutdown: Stop scheduler and cleanup
    logger.info("Stopping background scheduler...")
    stop_scheduler()
    logger.info("Application shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=lifespan
    )
    
    # Add middleware for automatic tool execution logging
    app.add_middleware(ToolLoggingMiddleware)
    
    # Include API routes
    app.include_router(router)
    
    return app


app = create_app()
