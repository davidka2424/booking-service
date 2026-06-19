from taskiq import TaskiqEvents, TaskiqState
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import create_db_engine, dispose_db_engine

settings = get_settings()

result_backend: RedisAsyncResultBackend = RedisAsyncResultBackend(  # type: ignore[type-arg]
    redis_url=settings.redis_url,
)

broker: ListQueueBroker = ListQueueBroker(
    url=settings.redis_url,
).with_result_backend(result_backend)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def on_worker_startup(state: TaskiqState) -> None:
    setup_logging()
    await create_db_engine()


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def on_worker_shutdown(state: TaskiqState) -> None:
    await dispose_db_engine()