from io import BytesIO

import pytest
from fastapi import UploadFile

from app.services.upload_client import UploadServiceError, upload_client


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_content_type():
    file = UploadFile(filename="payload.exe", file=BytesIO(b"abc"), size=3)
    file.headers = {"content-type": "application/octet-stream"}
    with pytest.raises(UploadServiceError) as exc:
        await upload_client._validate_upload(file)
    assert exc.value.status_code == 415
