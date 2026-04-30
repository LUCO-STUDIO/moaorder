from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    type: str
    channel: str
    status: str
    title: str
    body: Optional[str] = None
    payload: dict[str, Any]
    read_at: Optional[str] = None
    created_at: str


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    limit: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int
