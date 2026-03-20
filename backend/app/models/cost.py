import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey


class TotalCostEstimate(Base, UUIDPrimaryKey):
    __tablename__ = "total_cost_estimate"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offer.id", ondelete="CASCADE"), nullable=False
    )
    buyer_country: Mapped[str] = mapped_column(String(2), nullable=False)

    base_price_local: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    exchange_rate: Mapped[float | None] = mapped_column(Numeric(12, 6))
    exchange_spread: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.015)
    shipping_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    import_duty: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    import_vat: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    customs_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    total_cost_low: Mapped[float | None] = mapped_column(Numeric(12, 2))
    total_cost_high: Mapped[float | None] = mapped_column(Numeric(12, 2))
    confidence: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    sources: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    computed_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    __table_args__ = (
        UniqueConstraint("offer_id", "buyer_country", name="uq_total_cost_offer_country"),
        Index("idx_total_cost_offer", "offer_id"),
    )


class ImportRule(Base, UUIDPrimaryKey):
    __tablename__ = "import_rule"

    buyer_country: Mapped[str] = mapped_column(String(2), nullable=False)
    product_category: Mapped[str | None] = mapped_column(String(50))
    origin_country: Mapped[str | None] = mapped_column(String(2))
    duty_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0)
    vat_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    de_minimis_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    de_minimis_currency: Mapped[str | None] = mapped_column(String(3))
    customs_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[date] = mapped_column(nullable=False)
    valid_until: Mapped[date | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    __table_args__ = (
        Index("idx_import_rule_lookup", "buyer_country", "product_category"),
    )


class CurrencyRate(Base, UUIDPrimaryKey):
    __tablename__ = "currency_rate"

    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ecb")
    observed_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", "observed_at", name="uq_currency_rate"),
        Index("idx_currency_pair", "from_currency", "to_currency", "observed_at"),
    )
