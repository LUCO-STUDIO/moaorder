from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import require_owner
from app.models.user import User
from app.schemas.group import PresignRequest, PresignResponse
from app.services.storage import generate_presigned_upload

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/presign", response_model=PresignResponse)
async def presign_upload(
    body: PresignRequest,
    current_user: Annotated[User, Depends(require_owner)],
) -> PresignResponse:
    upload_url, public_url = generate_presigned_upload(
        body.filename,
        body.content_type,
    )
    return PresignResponse(upload_url=upload_url, public_url=public_url)
