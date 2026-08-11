import asyncio
import logging
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._memory: dict[str, dict[int, int]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    @staticmethod
    def _client_key(request: Request) -> str:
        client_ip = request.client.host if request.client else "unknown"
        return f"{client_ip}:{request.method}:{request.url.path}"

    async def _memory_increment(self, key: str, bucket: int) -> int:
        async with self._lock:
            buckets = self._memory[key]
            buckets[bucket] = buckets.get(bucket, 0) + 1
            for stale in [b for b in buckets if b < bucket - 1]:
                del buckets[stale]
            return buckets[bucket]

    async def _redis_increment(self, key: str, bucket: int) -> int:
        client = redis_manager.client
        if client is None:
            raise RuntimeError("Redis rate limiter requested before Redis is available")
        redis_key = f"{settings.RATE_LIMIT_PREFIX}:{bucket}:{key}"
        value = await client.incr(redis_key)
        if value == 1:
            await client.expire(redis_key, settings.RATE_LIMIT_WINDOW_SECONDS + 2)
        return int(value)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in settings.rate_limit_exempt_paths:
            return await call_next(request)

        now = int(time.time())
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        bucket = now // window
        key = self._client_key(request)

        try:
            if settings.RATE_LIMIT_BACKEND == "redis":
                count = await self._redis_increment(key, bucket)
            else:
                count = await self._memory_increment(key, bucket)
        except Exception:
            logger.exception("Rate limiter backend failed")
            if settings.RATE_LIMIT_FAIL_OPEN:
                return await call_next(request)
            return JSONResponse(status_code=503, content={"detail": "Rate limiter unavailable"})

        remaining = max(0, settings.RATE_LIMIT_REQUESTS - count)
        reset_seconds = window - (now % window)
        if count > settings.RATE_LIMIT_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={
                    "Retry-After": str(reset_seconds),
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_REQUESTS),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
