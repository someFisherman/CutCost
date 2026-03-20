"""ARQ worker settings and task definitions."""

import logging
from datetime import timedelta

from arq import cron
from arq.connections import RedisSettings

from app.config import settings

logger = logging.getLogger(__name__)


async def run_crawl_cycle(ctx: dict) -> None:
    """Execute pending crawl jobs for all active merchants."""
    from app.database import async_session
    from app.workers.tasks import execute_pending_crawl_jobs

    async with async_session() as db:
        count = await execute_pending_crawl_jobs(db)
        logger.info("Crawl cycle completed: %d jobs processed", count)


async def update_currencies(ctx: dict) -> None:
    """Fetch latest exchange rates from ECB."""
    from app.database import async_session
    from app.services.currency_service import update_currency_rates

    async with async_session() as db:
        count = await update_currency_rates(db)
        logger.info("Updated %d currency rates", count)


async def startup(ctx: dict) -> None:
    logger.info("ARQ worker started")


async def shutdown(ctx: dict) -> None:
    logger.info("ARQ worker shutting down")


class WorkerSettings:
    functions = [run_crawl_cycle, update_currencies]
    cron_jobs = [
        cron(run_crawl_cycle, hour={0, 4, 8, 12, 16, 20}, minute=0),
        cron(update_currencies, hour={6, 12, 18}, minute=5),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = timedelta(seconds=120)
