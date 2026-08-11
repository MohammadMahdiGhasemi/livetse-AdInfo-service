import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - surfaced clearly when Redis is enabled
    Redis = None  # type: ignore


class RedisManager:
    def __init__(self):
        self.client = None

    async def start(self) -> None:
        if not settings.REDIS_ENABLED:
            return
        if Redis is None:
            raise RuntimeError("REDIS_ENABLED=true but the redis package is not installed")
        if not settings.REDIS_URL:
            raise RuntimeError("REDIS_ENABLED=true requires REDIS_URL")

        self.client = Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
        )
        await self.client.ping()
        logger.info("Redis connectivity verified")

    async def close(self) -> None:
        if self.client is not None:
            await self.client.aclose()
            self.client = None


redis_manager = RedisManager()
