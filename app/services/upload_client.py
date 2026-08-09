import logging
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import httpx
from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)


class UploadServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class UploadServiceClient:
    def __init__(self):
        self.base_url = settings.UPLOAD_SERVICE_URL.rstrip("/")
        self.api_key = settings.UPLOAD_SERVICE_API_KEY
        self._headers = {"X-API-Key": self.api_key}
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        if self._client is None:
            timeout = httpx.Timeout(
                connect=settings.UPLOAD_CONNECT_TIMEOUT,
                read=settings.UPLOAD_READ_TIMEOUT,
                write=settings.UPLOAD_READ_TIMEOUT,
                pool=settings.UPLOAD_CONNECT_TIMEOUT,
            )
            limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
            self._client = httpx.AsyncClient(timeout=timeout, limits=limits)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            await self.start()
        assert self._client is not None
        return self._client

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    @staticmethod
    def _safe_filename(filename: str | None) -> str:
        return Path(filename or "upload.bin").name

    async def _validate_upload(self, file: UploadFile) -> None:
        content_type = (file.content_type or "").lower()
        if content_type not in settings.allowed_upload_content_types:
            raise UploadServiceError(415, "Unsupported upload content type")

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file.size is not None and file.size > max_bytes:
            raise UploadServiceError(413, "Upload exceeds maximum allowed size")

        # UploadFile is backed by a SpooledTemporaryFile. Check its actual size
        # without reading the whole payload into application memory.
        current = file.file.tell()
        file.file.seek(0, 2)
        actual_size = file.file.tell()
        file.file.seek(current)
        if actual_size > max_bytes:
            raise UploadServiceError(413, "Upload exceeds maximum allowed size")

    async def upload_file(
        self,
        file: UploadFile,
        folder: Optional[str] = None,
        default_folder: Optional[str] = None,
    ) -> dict:
        await self._validate_upload(file)
        target_folder = folder or default_folder or settings.BANNERS_UPLOAD_FOLDER
        client = await self._get_client()
        await file.seek(0)

        files = {
            "file": (
                self._safe_filename(file.filename),
                file.file,
                file.content_type or "application/octet-stream",
            )
        }
        data = {"folder": target_folder}

        try:
            resp = await client.post(
                self._url("/upload"),
                headers=self._headers,
                files=files,
                data=data,
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.TimeoutException as exc:
            logger.warning("Upload service timeout: %s", exc)
            raise UploadServiceError(504, "Upload service timed out") from exc
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            logger.error("Upload service error status=%s body=%r", exc.response.status_code, body)
            raise UploadServiceError(502, "Upload service rejected the request") from exc
        except (httpx.HTTPError, ValueError) as exc:
            logger.error("Upload service request failed: %s", exc)
            raise UploadServiceError(502, "Upload service unavailable") from exc

        if not isinstance(payload, dict):
            raise UploadServiceError(502, "Upload service returned an invalid response")
        upload_data = payload.get("data")
        if not isinstance(upload_data, dict) or not upload_data.get("url"):
            logger.error("Upload service response missing data.url")
            raise UploadServiceError(502, "Upload service returned an invalid response")
        return payload

    async def delete_file(self, folder: str, filename: str) -> dict:
        client = await self._get_client()
        safe_folder = quote(folder, safe="")
        safe_filename = quote(filename, safe="")
        try:
            resp = await client.delete(
                self._url(f"/folders/{safe_folder}/files/{safe_filename}"),
                headers=self._headers,
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.TimeoutException as exc:
            raise UploadServiceError(504, "Upload service timed out") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Upload delete failed status=%s body=%r",
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise UploadServiceError(502, "Upload service rejected the delete request") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise UploadServiceError(502, "Upload service unavailable") from exc
        return payload if isinstance(payload, dict) else {}

    async def get_serve_url(self, folder: str, filename: str) -> str:
        return f"{self.base_url}/serve/{quote(folder, safe='')}/{quote(filename, safe='')}"


upload_client = UploadServiceClient()
