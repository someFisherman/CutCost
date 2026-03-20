import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Offer(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "offer"

    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variant.id", ondelete="SET NULL")
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchant.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    affiliate_url: Mapped[str | None] = mapped_column(Text)
    raw_title: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_attributes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    identifiers_found: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    price_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False)

    shipping_cost: Mapped[float | None] = mapped_column(Numeric(10, 2))
    shipping_currency: Mapped[str | None] = mapped_column(String(3))
    shipping_source: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    delivery_days_min: Mapped[int | None] = mapped_column()
    delivery_days_max: Mapped[int | None] = mapped_column()

    condition: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    availability: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")

    match_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    match_method: Mapped[str | None] = mapped_column(String(30))
    match_reasons: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    mismatch_flags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    reviewed_at: Mapped[datetime | None] = mapped_column()

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_checked: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)
    last_price_change: Mapped[datetime | None] = mapped_column()
    check_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    product_variant: Mapped["ProductVariant | None"] = relationship(back_populates="offers")  # noqa: F821
    merchant: Mapped["Merchant"] = relationship(back_populates="offers")  # noqa: F821
    price_snapshots: Mapped[list["OfferPriceSnapshot"]] = relationship(
        back_populates="offer", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_offer_variant_active", "product_variant_id",
              postgresql_where="is_active = true"),
        Index("idx_offer_review", "review_status",
              postgresql_where="review_status = 'pending'"),
    )


class OfferPriceSnapshot(Base, UUIDPrimaryKey):
    __tablename__ = "offer_price_snapshot"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offer.id", ondelete="CASCADE"), nullable=False
    )
    price_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    availability: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    observed_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    offer: Mapped["Offer"] = relationship(back_populates="price_snapshots")

    __table_args__ = (
        Index("idx_price_snapshot_offer_time", "offer_id", "observed_at"),
    )
