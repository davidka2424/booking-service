from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.core.config import get_settings

settings = get_settings()

result_backend: RedisAsyncResultBackend = RedisAsyncResultBackend(  # type: ignore[type-arg]
    redis_url=settings.redis_url,
)

broker: ListQueueBroker = ListQueueBroker(
    url=settings.redis_url,
).with_result_backend(result_backend)
