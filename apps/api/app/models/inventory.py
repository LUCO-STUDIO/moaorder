import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class InventoryHold(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "inventory_holds"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    portone_payment_id: Mapped[Optional[str]] = mapped_column(String(200))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'converted', 'expired')",
            name="ck_inventory_holds_status",
        ),
        Index(
            "idx_holds_expires",
            "expires_at",
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "idx_holds_active_user_group",
            "user_id",
            "group_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "idx_holds_payment",
            "portone_payment_id",
            unique=True,
            postgresql_where=text("portone_payment_id IS NOT NULL"),
        ),
    )
