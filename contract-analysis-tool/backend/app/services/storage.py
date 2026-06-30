from __future__ import annotations

import io
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError

from app.config import get_settings
from app.dependencies import get_s3_client


class StorageService:
    def __init__(self):
        self.settings = get_settings()
        self.local_root = Path(self.settings.local_storage_dir).resolve()

    def put_bytes(self, key: str, body: bytes, content_type: str | None = None) -> str:
        if self._try_put_s3(key, body, content_type):
            return key
        if not self.settings.use_local_storage_fallback:
            raise RuntimeError("Unable to store file in S3 and local fallback disabled")
        local_path = self._local_path_for_key(key)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(body)
        return f"local://{key}"

    def get_bytes(self, key: str) -> bytes:
        if key.startswith("local://"):
            local_key = key.replace("local://", "", 1)
            return self._local_path_for_key(local_key).read_bytes()

        data = self._try_get_s3(key)
        if data is not None:
            return data

        if not self.settings.use_local_storage_fallback:
            raise RuntimeError("Unable to read file from S3 and local fallback disabled")
        return self._local_path_for_key(key).read_bytes()

    def _local_path_for_key(self, key: str) -> Path:
        return self.local_root.joinpath(*key.split("/"))

    def _try_put_s3(self, key: str, body: bytes, content_type: str | None) -> bool:
        try:
            s3 = get_s3_client()
            s3.put_object(
                Bucket=self.settings.s3_bucket,
                Key=key,
                Body=body,
                ContentType=content_type or "application/octet-stream",
            )
            return True
        except (EndpointConnectionError, ClientError, BotoCoreError, OSError):
            return False

    def _try_get_s3(self, key: str) -> bytes | None:
        try:
            s3 = get_s3_client()
            response = s3.get_object(Bucket=self.settings.s3_bucket, Key=key)
            stream = response.get("Body")
            if isinstance(stream, io.BytesIO):
                return stream.getvalue()
            if stream is None:
                return None
            return stream.read()
        except (EndpointConnectionError, ClientError, BotoCoreError, OSError):
            return None
