import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Merchant(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "merchant"

    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    website: Mapped[str] = mapped_column(String(500), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    is_marketplace: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_curated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    affiliate_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    extraction_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    domains: Mapped[list["MerchantDomain"]] = relationship(
        back_populates="merchant", cascade="all, delete-orphan"
    )
    shipping_rules: Mapped[list["MerchantShippingRule"]] = relationship(
        back_populates="merchant", cascade="all, delete-orphan"
    )
    offers: Mapped[list["Offer"]] = relationship(back_populates="merchant")  # noqa: F821
    trust_signals: Mapped[list["TrustSignal"]] = relationship(back_populates="merchant")  # noqa: F821
    trust_scores: Mapped[list["TrustScore"]] = relationship(back_populates="merchant")  # noqa: F821


class MerchantDomain(Base, UUIDPrimaryKey):
    __tablename__ = "merchant_domain"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchant.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(253), nullable=False, unique=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    whois_created: Mapped[date | None] = mapped_column(Date)
    has_https: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    merchant: Mapped["Merchant"] = relationship(back_populates="domains")


class MerchantShippingRule(Base, UUIDPrimaryKey):
    __tablename__ = "merchant_shipping_rule"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchant.id", ondelete="CASCADE"), nullable=False
    )
    destination_country: Mapped[str] = mapped_column(String(2), nullable=False)
    cost_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    cost_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CHF")
    free_above: Mapped[float | None] = mapped_column(Numeric(10, 2))
    estimated_days_min: Mapped[int | None] = mapped_column()
    estimated_days_max: Mapped[int | None] = mapped_column()
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="curated")
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    merchant: Mapped["Merchant"] = relationship(back_populates="shipping_rules")

    __table_args__ = (
        UniqueConstraint("merchant_id", "destination_country", name="uq_merchant_shipping"),
    )
