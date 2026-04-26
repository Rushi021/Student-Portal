"""File storage abstraction: local disk (dev) or Amazon S3 (AWS).

Set ``USE_S3=true`` and ``S3_BUCKET_NAME`` on Elastic Beanstalk / EC2 with an IAM role
that allows ``s3:PutObject`` and ``s3:GetObject`` (and ``s3:DeleteObject`` if you add deletes).

Presigned GET URLs are used for view/download so large PDFs are not proxied through Gunicorn.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from flask import current_app


def _safe_filename_stem(name: str) -> str:
    s = re.sub(r"[^\w.\- ]+", "", name, flags=re.UNICODE).strip() or "document"
    return s[:200]


class StorageBackend:
    def save_pdf(self, file_storage, original_filename: str) -> str:
        """Return a stored identifier (local relative path or S3 key)."""
        raise NotImplementedError

    def save_pdf_bytes(self, data: bytes, original_filename: str = "file.pdf") -> str:
        """Store raw PDF bytes (e.g. seed data). Same identifier rules as :meth:`save_pdf`."""
        raise NotImplementedError

    def download_url_or_path(
        self,
        file_key: str,
        *,
        download_name: str = "file.pdf",
        as_attachment: bool = False,
    ) -> tuple[str, str]:
        """Return (kind, value) where kind is ``local`` (filesystem path) or ``redirect`` (URL)."""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    def save_pdf(self, file_storage, original_filename: str) -> str:
        folder = Path(current_app.config["UPLOAD_FOLDER"])
        folder.mkdir(parents=True, exist_ok=True)
        ext = Path(original_filename).suffix.lower() or ".pdf"
        if ext != ".pdf":
            ext = ".pdf"
        name = f"{uuid.uuid4().hex}{ext}"
        dest = folder / name
        file_storage.save(dest)
        return name

    def save_pdf_bytes(self, data: bytes, original_filename: str = "file.pdf") -> str:
        folder = Path(current_app.config["UPLOAD_FOLDER"])
        folder.mkdir(parents=True, exist_ok=True)
        ext = Path(original_filename).suffix.lower() or ".pdf"
        if ext != ".pdf":
            ext = ".pdf"
        name = f"{uuid.uuid4().hex}{ext}"
        (folder / name).write_bytes(data)
        return name

    def download_url_or_path(
        self,
        file_key: str,
        *,
        download_name: str = "file.pdf",
        as_attachment: bool = False,
    ) -> tuple[str, str]:
        path = Path(current_app.config["UPLOAD_FOLDER"]) / file_key
        return "local", str(path.resolve())


class S3Storage(StorageBackend):
    def _client(self):
        import boto3

        return boto3.client("s3", region_name=current_app.config.get("AWS_REGION", "us-east-1"))

    def save_pdf(self, file_storage, original_filename: str) -> str:
        bucket = current_app.config["S3_BUCKET_NAME"]
        prefix = current_app.config.get("S3_MATERIALS_PREFIX", "materials/")
        ext = Path(original_filename).suffix.lower() or ".pdf"
        key = f"{prefix}{uuid.uuid4().hex}{ext}"
        file_storage.stream.seek(0)
        self._client().upload_fileobj(
            file_storage.stream,
            bucket,
            key,
            ExtraArgs={"ContentType": "application/pdf"},
        )
        return key

    def save_pdf_bytes(self, data: bytes, original_filename: str = "file.pdf") -> str:
        bucket = current_app.config["S3_BUCKET_NAME"]
        prefix = current_app.config.get("S3_MATERIALS_PREFIX", "materials/")
        ext = Path(original_filename).suffix.lower() or ".pdf"
        key = f"{prefix}{uuid.uuid4().hex}{ext}"
        self._client().put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType="application/pdf",
        )
        return key

    def download_url_or_path(
        self,
        file_key: str,
        *,
        download_name: str = "file.pdf",
        as_attachment: bool = False,
    ) -> tuple[str, str]:
        bucket = current_app.config["S3_BUCKET_NAME"]
        client = self._client()
        safe = _safe_filename_stem(download_name)
        if not safe.lower().endswith(".pdf"):
            safe = f"{safe}.pdf"
        disp = f'attachment; filename="{safe}"' if as_attachment else f'inline; filename="{safe}"'
        expires = int(current_app.config.get("S3_PRESIGN_EXPIRES", 3600))
        url = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket,
                "Key": file_key,
                "ResponseContentType": "application/pdf",
                "ResponseContentDisposition": disp,
            },
            ExpiresIn=expires,
        )
        return "redirect", url


def get_storage() -> StorageBackend:
    if current_app.config.get("USE_S3"):
        if not current_app.config.get("S3_BUCKET_NAME"):
            raise RuntimeError("S3_BUCKET_NAME must be set when USE_S3 is true.")
        return S3Storage()
    return LocalStorage()
