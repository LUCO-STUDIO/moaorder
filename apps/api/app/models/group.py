from __future__ import annotations

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
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Group(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "groups"

    public_id: Mapped[str] = mapped_column(
        String(12), unique=True, nullable=False
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="open"
    )
    type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="reservation"
    )
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    max_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    remaining_qty: Mapped[Optional[int]] = mapped_column(Integer)
    min_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    closes_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(200))

    pickup_slots: Mapped[list[GroupPickupSlot]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'closed', 'pickup_ready', 'completed', 'cancelled')",
            name="ck_groups_status",
        ),
        CheckConstraint(
            "type IN ('reservation', 'group_buy', 'pickup')",
            name="ck_groups_type",
        ),
        Index("idx_groups_store_status", "store_id", "status"),
        Index(
            "idx_groups_closes_at",
            "closes_at",
            postgresql_where=text("status = 'open'"),
        ),
    )


class GroupPickupSlot(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "group_pickup_slots"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    group: Mapped[Group] = relationship(back_populates="pickup_slots")

    __table_args__ = (
        Index("idx_pickup_slots_group", "group_id"),
    )
