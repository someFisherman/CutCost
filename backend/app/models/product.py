import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Product(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "product"

    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    product_line: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    image_url: Mapped[str | None] = mapped_column(Text)
    release_date: Mapped[date | None] = mapped_column(Date)
    discontinued: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    aliases: Mapped[list["ProductSearchAlias"]] = relationship(back_populates="product")

    __table_args__ = (
        Index("idx_product_search_trgm", "canonical_name", postgresql_using="gin",
              postgresql_ops={"canonical_name": "gin_trgm_ops"}),
    )


class ProductVariant(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "product_variant"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product.id", ondelete="CASCADE"), nullable=False
    )
    variant_key: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(600), nullable=False, unique=True, index=True)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="variants")
    identifiers: Mapped[list["ProductIdentifier"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )
    offers: Mapped[list["Offer"]] = relationship(back_populates="product_variant")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("product_id", "variant_key", name="uq_variant_key"),
        Index("idx_variant_display_trgm", "display_name", postgresql_using="gin",
              postgresql_ops={"display_name": "gin_trgm_ops"}),
    )


class ProductIdentifier(Base, UUIDPrimaryKey):
    __tablename__ = "product_identifier"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variant.id", ondelete="CASCADE"), nullable=False
    )
    identifier_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(
        server_default="now()", nullable=False
    )

    variant: Mapped["ProductVariant"] = relationship(back_populates="identifiers")

    __table_args__ = (
        UniqueConstraint("identifier_type", "value", name="uq_identifier"),
        Index("idx_identifier_lookup", "identifier_type", "value"),
    )


class ProductSearchAlias(Base, UUIDPrimaryKey):
    __tablename__ = "product_search_alias"

    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variant.id", ondelete="CASCADE")
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product.id", ondelete="CASCADE")
    )
    alias: Mapped[str] = mapped_column(String(500), nullable=False)

    product: Mapped["Product | None"] = relationship(back_populates="aliases")

    __table_args__ = (
        Index("idx_alias_trgm", "alias", postgresql_using="gin",
              postgresql_ops={"alias": "gin_trgm_ops"}),
    )
