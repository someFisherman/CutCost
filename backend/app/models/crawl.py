import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey


class CrawlJob(Base, UUIDPrimaryKey):
    __tablename__ = "crawl_job"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchant.id", ondelete="CASCADE"), nullable=False
    )
    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variant.id", ondelete="SET NULL")
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    strategy: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    scheduled_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()

    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    error_message: Mapped[str | None] = mapped_column(Text)
    error_category: Mapped[str | None] = mapped_column(String(30))

    recurrence_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    next_run: Mapped[datetime | None] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    __table_args__ = (
        Index("idx_crawl_pending", "status",
              postgresql_where="status IN ('pending', 'running')"),
        Index("idx_crawl_next_run", "next_run",
              postgresql_where="status != 'blocked'"),
    )


class ExtractionResult(Base, UUIDPrimaryKey):
    __tablename__ = "extraction_result"

    crawl_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crawl_job.id", ondelete="CASCADE"), nullable=False
    )
    offer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offer.id", ondelete="SET NULL")
    )

    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    extracted_title: Mapped[str | None] = mapped_column(Text)
    extracted_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    extracted_currency: Mapped[str | None] = mapped_column(String(3))
    extracted_ean: Mapped[str | None] = mapped_column(String(20))
    extracted_availability: Mapped[str | None] = mapped_column(String(20))

    parsing_method: Mapped[str | None] = mapped_column(String(20))
    llm_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    llm_model: Mapped[str | None] = mapped_column(String(50))
    llm_tokens: Mapped[int | None] = mapped_column()
    llm_cost_usd: Mapped[float | None] = mapped_column(Numeric(8, 6))

    extraction_quality: Mapped[float | None] = mapped_column(Numeric(3, 2))
    validation_errors: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    __table_args__ = (
        Index("idx_extraction_crawl", "crawl_job_id"),
    )
