from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import get_logger, setup_logging
from app.db.session import create_db_engine, dispose_db_engine
from app.workers.broker import broker

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    setup_logging()
    logger.info("Starting booking service")

    await create_db_engine()
    logger.info("Database engine initialized")

    await broker.startup()
    logger.info("TaskIQ broker started")

    yield

    # Shutdown
    logger.info("Shutting down booking service")
    await broker.shutdown()
    await dispose_db_engine()
    logger.info("Shutdown complete")
