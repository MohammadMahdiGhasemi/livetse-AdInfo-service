from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from jwt.algorithms import RSAAlgorithm

from app.core.config import settings

logger = logging.getLogger(__name__)


class JwksError(Exception):
    pass


class JwksClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._keys: dict[str, Any] = {}
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._client is not None or not settings.JWT_JWKS_URL:
            return
        timeout = httpx.Timeout(
            connect=settings.JWT_JWKS_CONNECT_TIMEOUT,
            read=settings.JWT_JWKS_READ_TIMEOUT,
            write=settings.JWT_JWKS_READ_TIMEOUT,
            pool=settings.JWT_JWKS_CONNECT_TIMEOUT,
        )
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._keys.clear()
        self._expires_at = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            await self.start()
        if self._client is None:
            raise JwksError("JWKS client is not configured")
        return self._client

    async def _refresh(self, *, force: bool = False) -> None:
        if not settings.JWT_JWKS_URL:
            raise JwksError("JWT_JWKS_URL is not configured")

        now = time.monotonic()
        if not force and self._keys and now < self._expires_at:
            return

        async with self._lock:
            now = time.monotonic()
            if not force and self._keys and now < self._expires_at:
                return

            client = await self._get_client()
            try:
                response = await client.get(settings.JWT_JWKS_URL)
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("Failed to refresh JWKS: %s", exc.__class__.__name__)
                raise JwksError("Unable to load JWT signing keys") from exc

            raw_keys = payload.get("keys") if isinstance(payload, dict) else None
            if not isinstance(raw_keys, list):
                raise JwksError("Invalid JWKS response")

            parsed: dict[str, Any] = {}
            for item in raw_keys:
                if not isinstance(item, dict):
                    continue
                kid = str(item.get("kid") or "").strip()
                if not kid:
                    continue
                if item.get("kty") != "RSA":
                    continue
                use = item.get("use")
                if use not in (None, "sig"):
                    continue
                alg = item.get("alg")
                if alg not in (None, "RS256"):
                    continue
                try:
                    parsed[kid] = RSAAlgorithm.from_jwk(item)
                except Exception:
                    logger.warning("Ignoring malformed RSA JWK kid=%s", kid)

            if not parsed:
                raise JwksError("JWKS contains no usable RS256 keys")

            self._keys = parsed
            self._expires_at = time.monotonic() + settings.JWT_JWKS_CACHE_TTL_SECONDS

    async def get_key(self, kid: str) -> Any:
        await self._refresh()
        key = self._keys.get(kid)
        if key is not None:
            return key

        # The issuer may have rotated keys. Refresh once immediately before
        # rejecting an unknown kid.
        await self._refresh(force=True)
        key = self._keys.get(kid)
        if key is None:
            raise JwksError("Unknown JWT signing key")
        return key


jwks_client = JwksClient()
