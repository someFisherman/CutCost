"""Search & Query Understanding Service.

Handles query normalization, autocomplete, product lookup, and disambiguation.
"""

import re
import unicodedata

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product, ProductSearchAlias, ProductVariant


def normalize_query(raw: str) -> str:
    """Lowercase, strip accents, collapse whitespace, remove special chars."""
    text = raw.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s\-.]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def autocomplete(
    db: AsyncSession, partial: str, limit: int = 6
) -> list[dict]:
    """Return product suggestions matching partial input."""
    if len(partial) < 2:
        return []

    normalized = normalize_query(partial)

    # pg_trgm similarity search on product variants
    results = await db.execute(
        select(ProductVariant)
        .join(Product)
        .where(
            or_(
                func.similarity(ProductVariant.display_name, normalized) > 0.1,
                ProductVariant.display_name.ilike(f"%{normalized}%"),
            )
        )
        .order_by(func.similarity(ProductVariant.display_name, normalized).desc())
        .limit(limit)
        .options(selectinload(ProductVariant.product))
    )
    variants = results.scalars().all()

    return [
        {
            "variant_id": str(v.id),
            "product_id": str(v.product_id),
            "display_name": v.display_name,
            "slug": v.slug,
            "category": v.product.category,
            "brand": v.product.brand,
            "image_url": v.image_url or v.product.image_url,
        }
        for v in variants
    ]


async def search_products(
    db: AsyncSession, query: str
) -> dict:
    """
    Search for products matching a query.

    Returns:
        - exact_variant: if query matches one variant clearly
        - variants: if query matches multiple variants of same product (disambiguation)
        - products: if query matches multiple products
        - empty: if no match
    """
    normalized = normalize_query(query)

    # 1. Try exact slug match
    variant = await db.execute(
        select(ProductVariant)
        .where(ProductVariant.slug == _slugify(normalized))
        .options(selectinload(ProductVariant.product))
    )
    exact = variant.scalar_one_or_none()
    if exact:
        return {"type": "exact", "variant": exact, "variants": [], "products": []}

    # 2. Try alias match
    alias_result = await db.execute(
        select(ProductSearchAlias)
        .where(ProductSearchAlias.alias == normalized)
    )
    alias = alias_result.scalar_one_or_none()
    if alias and alias.variant_id:
        v = await db.get(ProductVariant, alias.variant_id, options=[selectinload(ProductVariant.product)])
        if v:
            return {"type": "exact", "variant": v, "variants": [], "products": []}

    # 3. Full-text + trigram search on variants
    results = await db.execute(
        select(ProductVariant)
        .join(Product)
        .where(
            or_(
                ProductVariant.display_name.ilike(f"%{normalized}%"),
                func.similarity(ProductVariant.display_name, normalized) > 0.15,
            )
        )
        .order_by(func.similarity(ProductVariant.display_name, normalized).desc())
        .limit(20)
        .options(selectinload(ProductVariant.product))
    )
    matches = results.scalars().all()

    if not matches:
        return {"type": "empty", "variant": None, "variants": [], "products": []}

    if len(matches) == 1:
        return {"type": "exact", "variant": matches[0], "variants": [], "products": []}

    # Check if all matches are variants of the same product
    product_ids = {m.product_id for m in matches}
    if len(product_ids) == 1:
        return {"type": "disambiguation", "variant": None, "variants": matches, "products": []}

    return {"type": "multiple", "variant": None, "variants": matches[:10], "products": []}


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")
