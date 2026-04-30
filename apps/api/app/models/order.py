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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Order(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "orders"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="paid"
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    current_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    current_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_id: Mapped[Optional[str]] = mapped_column(String(200))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    pickup_slot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_pickup_slots.id")
    )
    cancel_requested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    cancel_request_reason: Mapped[Optional[str]] = mapped_column(String(200))

    adjustments: Mapped[list[OrderAdjustment]] = relationship(
        back_populates="order", lazy="selectin"
    )
    events: Mapped[list[OrderEvent]] = relationship(
        back_populates="order", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('paid', 'confirmed', 'pickup_ready', "
            "'picked_up', 'not_picked_up', 'cancelled')",
            name="ck_orders_status",
        ),
        Index("idx_orders_group", "group_id"),
        Index("idx_orders_user", "user_id"),
        Index("idx_orders_store_status", "store_id", "status"),
        Index(
            "idx_orders_group_user_active",
            "group_id",
            "user_id",
            unique=True,
            postgresql_where=text(
                "status IN ('paid', 'confirmed', 'pickup_ready')"
            ),
        ),
        Index(
            "idx_orders_payment",
            "payment_id",
            unique=True,
            postgresql_where=text("payment_id IS NOT NULL"),
        ),
    )


class OrderAdjustment(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "order_adjustments"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    refund_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    refund_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending"
    )
    refund_payment_id: Mapped[Optional[str]] = mapped_column(String(200))
    reason: Mapped[Optional[str]] = mapped_column(String(200))
    requested_by: Mapped[str] = mapped_column(String(20), nullable=False)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="adjustments")

    __table_args__ = (
        CheckConstraint(
            "type IN ('quantity_reduce', 'full_cancel', 'admin_cancel', 'system_cancel')",
            name="ck_order_adjustments_type",
        ),
        CheckConstraint(
            "refund_status IN ('pending', 'completed', 'failed')",
            name="ck_order_adjustments_refund_status",
        ),
        CheckConstraint(
            "requested_by IN ('customer', 'owner', 'system')",
            name="ck_order_adjustments_requested_by",
        ),
        Index("idx_adjustments_order", "order_id"),
        Index(
            "idx_adjustments_refund",
            "refund_status",
            postgresql_where=text("refund_status = 'pending'"),
        ),
    )


class OrderEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "order_events"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    actor_type: Mapped[Optional[str]] = mapped_column(String(20))
    extra: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="events")

    __table_args__ = (
        CheckConstraint(
            "actor_type IN ('customer', 'owner', 'system')",
            name="ck_order_events_actor_type",
        ),
        Index("idx_events_order", "order_id", "created_at"),
    )
