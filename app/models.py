from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(primary_key=True)

    merchant_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    transactions = relationship(
        "Transaction",
        back_populates="merchant",
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)

    transaction_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    merchant_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("merchants.merchant_id"),
        nullable=False,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    payment_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="initiated",
    )

    settlement_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    merchant = relationship(
        "Merchant",
        back_populates="transactions",
    )

    events = relationship(
        "PaymentEvent",
        back_populates="transaction",
        order_by="PaymentEvent.event_timestamp",
    )

    __table_args__ = (
        Index("idx_transactions_merchant", "merchant_id"),
        Index("idx_transactions_payment_status", "payment_status"),
        Index("idx_transactions_created_at", "created_at"),
        Index(
            "idx_transactions_merchant_status",
            "merchant_id",
            "payment_status",
        ),
    )


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    transaction_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("transactions.transaction_id"),
        nullable=False,
    )

    merchant_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    transaction = relationship(
        "Transaction",
        back_populates="events",
    )

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            name="uq_payment_events_event_id",
        ),
        Index(
            "idx_events_transaction",
            "transaction_id",
        ),
        Index(
            "idx_events_merchant_timestamp",
            "merchant_id",
            "event_timestamp",
        ),
        Index(
            "idx_events_type",
            "event_type",
        ),
    )