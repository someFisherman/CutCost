import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey


class SearchQuery(Base, UUIDPrimaryKey):
    __tablename__ = "search_query"

    raw_query: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_query: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_entities: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    matched_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product.id")
    )
    matched_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variant.id")
    )
    disambiguation_shown: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    result_count: Mapped[int | None] = mapped_column()

    buyer_country: Mapped[str] = mapped_column(String(2), nullable=False, default="CH")
    session_id: Mapped[str | None] = mapped_column(String(100))
    user_agent: Mapped[str | None] = mapped_column(Text)

    response_time_ms: Mapped[int | None] = mapped_column()
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    __table_args__ = (
        Index("idx_search_date", "created_at"),
        Index("idx_search_product", "matched_product_id"),
    )


class SearchClick(Base, UUIDPrimaryKey):
    __tablename__ = "search_click"

    query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_query.id", ondelete="CASCADE"), nullable=False
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offer.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_affiliate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    __table_args__ = (
        Index("idx_click_query", "query_id"),
        Index("idx_click_offer", "offer_id"),
    )


class PriceAlert(Base, UUIDPrimaryKey):
    __tablename__ = "price_alert"

    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variant.id", ondelete="CASCADE"), nullable=False
    )
    target_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    buyer_country: Mapped[str] = mapped_column(String(2), nullable=False, default="CH")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_notified: Mapped[datetime | None] = mapped_column()
    notification_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    __table_args__ = (
        Index("idx_alert_variant_active", "product_variant_id",
              postgresql_where="is_active = true"),
    )
