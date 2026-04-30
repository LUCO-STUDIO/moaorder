from __future__ import annotations

import uuid

import boto3
from botocore.config import Config

from app.core.config import settings

_PRESIGN_EXPIRY = 600  # 10 minutes


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def generate_presigned_upload(
    filename: str,
    content_type: str,
) -> tuple[str, str]:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    key = f"groups/{uuid.uuid4()}.{ext}" if ext else f"groups/{uuid.uuid4()}"

    client = _get_s3_client()
    upload_url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.R2_BUCKET,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=_PRESIGN_EXPIRY,
    )

    public_url = f"{settings.R2_PUBLIC_BASE_URL}/{key}"
    return upload_url, public_url
