import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey


class TrustSignal(Base, UUIDPrimaryKey):
    __tablename__ = "trust_signal"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchant.id", ondelete="CASCADE"), nullable=False
    )
    signal_name: Mapped[str] = mapped_column(String(50), nullable=False)
    signal_value: Mapped[float | None] = mapped_column(Numeric(5, 3))
    raw_value: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=1.0)
    source: Mapped[str | None] = mapped_column(String(50))
    collected_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    merchant: Mapped["Merchant"] = relationship(back_populates="trust_signals")  # noqa: F821

    __table_args__ = (
        Index("idx_trust_signal_merchant", "merchant_id"),
    )


class TrustScore(Base, UUIDPrimaryKey):
    __tablename__ = "trust_score"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchant.id", ondelete="CASCADE"), nullable=False
    )
    overall_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    tier: Mapped[str] = mapped_column(String(10), nullable=False)  # high, medium, low, blocked
    signal_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    red_flags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    override_reason: Mapped[str | None] = mapped_column(Text)
    computed_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

    merchant: Mapped["Merchant"] = relationship(back_populates="trust_scores")  # noqa: F821

    __table_args__ = (
        Index("idx_trust_score_latest", "merchant_id", "computed_at"),
    )
