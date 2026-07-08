import logging
from typing import Optional
from fastapi import UploadFile
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

UPLOAD_TIMEOUT = 60.0


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

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    async def upload_file(
        self,
        file: UploadFile,
        folder: Optional[str] = None,
        default_folder: Optional[str] = None,
    ) -> dict:
        target_folder = folder or default_folder or settings.BANNERS_UPLOAD_FOLDER

        async with httpx.AsyncClient(timeout=UPLOAD_TIMEOUT) as client:
            files = {"file": (file.filename, await file.read(), file.content_type)}
            data = {"folder": target_folder}

            resp = await client.post(
                self._url("/upload"),
                headers=self._headers,
                files=files,
                data=data,
            )

        if resp.status_code >= 400:
            logger.error(f"Upload failed: {resp.status_code} - {resp.text}")
            raise UploadServiceError(resp.status_code, resp.text)

        return resp.json()

    async def delete_file(self, folder: str, filename: str) -> dict:
        async with httpx.AsyncClient(timeout=UPLOAD_TIMEOUT) as client:
            resp = await client.delete(
                self._url(f"/folders/{folder}/files/{filename}"),
                headers=self._headers,
            )

        if resp.status_code >= 400:
            logger.error(f"Delete failed: {resp.status_code} - {resp.text}")
            raise UploadServiceError(resp.status_code, resp.text)

        return resp.json()

    async def get_serve_url(self, folder: str, filename: str) -> str:
        return f"{self.base_url}/serve/{folder}/{filename}"


upload_client = UploadServiceClient()
