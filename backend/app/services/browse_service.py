"""Browse & Filter Service.

Provides product browsing with hierarchical filters, sorting,
and dynamic filter option discovery.
"""

import re
from dataclasses import dataclass

from sqlalchemy import Integer, String, case, cast, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.merchant import Merchant
from app.models.offer import Offer
from app.offer_visibility import (
    EXCLUDED_OFFER_MERCHANT_SLUGS,
    EXCLUDED_OFFER_URL_SUBSTRINGS,
)
from app.models.product import Product, ProductVariant
from app.models.trust import TrustScore


@dataclass
class BrowseFilters:
    q: str | None = None
    category: str | None = None
    brand: str | None = None
    product_line: str | None = None
    model: str | None = None
    storage: str | None = None
    color: str | None = None
    condition: str | None = None
    mode: str = "high_trust"
    sort: str = "best_deal"
    page: int = 1
    per_page: int = 24
    price_min: float | None = None
    price_max: float | None = None


@dataclass
class BrowseProduct:
    variant_id: str
    product_id: str
    display_name: str
    slug: str
    brand: str
    model: str
    category: str
    product_line: str | None
    attributes: dict
    image_url: str | None
    best_price: float | None
    best_price_currency: str | None
    offer_count: int
    best_trust_tier: str | None
    condition_available: list[str]


@dataclass
class FilterOption:
    value: str
    label: str
    count: int


@dataclass
class FilterOptions:
    categories: list[FilterOption]
    brands: list[FilterOption]
    product_lines: list[FilterOption]
    models: list[FilterOption]
    storages: list[FilterOption]
    colors: list[FilterOption]
    conditions: list[FilterOption]
    price_min: float | None
    price_max: float | None


async def browse_products(
    db: AsyncSession, filters: BrowseFilters
) -> tuple[list[BrowseProduct], int]:
    """Browse products with filters, returning matching variants with best prices."""

    excluded_merchant_ids = select(Merchant.id).where(
        Merchant.slug.in_(EXCLUDED_OFFER_MERCHANT_SLUGS)
    )
    curated_merchant_ids = select(Merchant.id).where(Merchant.is_curated == True)  # noqa: E712

    offer_exists_conditions = [
        Offer.product_variant_id == ProductVariant.id,
        Offer.is_active == True,  # noqa: E712
        ~Offer.merchant_id.in_(excluded_merchant_ids),
    ]
    if filters.condition and filters.condition != "all":
        offer_exists_conditions.append(Offer.condition == filters.condition)
    if filters.mode == "high_trust":
        offer_exists_conditions.append(Offer.merchant_id.in_(curated_merchant_ids))
    for broken_url in EXCLUDED_OFFER_URL_SUBSTRINGS:
        offer_exists_conditions.append(~Offer.url.contains(broken_url))

    has_eligible_offer = exists(
        select(1).select_from(Offer).where(*offer_exists_conditions)
    )

    query = (
        select(ProductVariant)
        .join(Product)
        .where(has_eligible_offer)
        .options(selectinload(ProductVariant.product))
    )

    if filters.q:
        normalized = filters.q.strip().lower()
        query = query.where(
            or_(
                ProductVariant.display_name.ilike(f"%{normalized}%"),
                Product.canonical_name.ilike(f"%{normalized}%"),
                Product.brand.ilike(f"%{normalized}%"),
                func.coalesce(Product.product_line, "").ilike(f"%{normalized}%"),
                func.similarity(ProductVariant.display_name, normalized) > 0.15,
                func.similarity(Product.canonical_name, normalized) > 0.15,
            )
        )

    if filters.category:
        query = query.where(Product.category == filters.category.lower())
    if filters.brand:
        query = query.where(func.lower(Product.brand) == filters.brand.lower())
    if filters.product_line:
        query = query.where(func.lower(Product.product_line) == filters.product_line.lower())
    if filters.model:
        query = query.where(func.lower(Product.model) == filters.model.lower())
    if filters.storage:
        query = query.where(
            func.lower(ProductVariant.attributes["storage"].astext) == filters.storage.lower()
        )
    if filters.color:
        query = query.where(
            func.lower(ProductVariant.attributes["color"].astext).contains(filters.color.lower())
        )

    query = query.order_by(Product.brand, Product.model, ProductVariant.display_name)

    count_q = (
        select(func.count(ProductVariant.id))
        .select_from(ProductVariant)
        .join(Product)
        .where(has_eligible_offer)
    )
    if filters.q:
        normalized = filters.q.strip().lower()
        count_q = count_q.where(
            or_(
                ProductVariant.display_name.ilike(f"%{normalized}%"),
                Product.canonical_name.ilike(f"%{normalized}%"),
                Product.brand.ilike(f"%{normalized}%"),
                func.coalesce(Product.product_line, "").ilike(f"%{normalized}%"),
                func.similarity(ProductVariant.display_name, normalized) > 0.15,
                func.similarity(Product.canonical_name, normalized) > 0.15,
            )
        )
    if filters.category:
        count_q = count_q.where(Product.category == filters.category.lower())
    if filters.brand:
        count_q = count_q.where(func.lower(Product.brand) == filters.brand.lower())
    if filters.product_line:
        count_q = count_q.where(func.lower(Product.product_line) == filters.product_line.lower())
    if filters.model:
        count_q = count_q.where(func.lower(Product.model) == filters.model.lower())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (filters.page - 1) * filters.per_page
    query = query.offset(offset).limit(filters.per_page)

    result = await db.execute(query)
    variants = result.scalars().all()

    browse_products_list: list[BrowseProduct] = []
    for v in variants:
        offer_info = await _get_variant_offer_summary(db, v.id, filters)

        if filters.price_min and offer_info["best_price"] and offer_info["best_price"] < filters.price_min:
            continue
        if filters.price_max and offer_info["best_price"] and offer_info["best_price"] > filters.price_max:
            continue

        browse_products_list.append(BrowseProduct(
            variant_id=str(v.id),
            product_id=str(v.product_id),
            display_name=v.display_name,
            slug=v.slug,
            brand=v.product.brand,
            model=v.product.model,
            category=v.product.category,
            product_line=v.product.product_line,
            attributes=v.attributes,
            image_url=v.image_url or v.product.image_url,
            best_price=offer_info["best_price"],
            best_price_currency=offer_info["currency"],
            offer_count=offer_info["count"],
            best_trust_tier=offer_info["best_trust_tier"],
            condition_available=offer_info["conditions"],
        ))

    if filters.sort == "price_asc":
        browse_products_list.sort(key=lambda p: p.best_price or 999999)
    elif filters.sort == "price_desc":
        browse_products_list.sort(key=lambda p: p.best_price or 0, reverse=True)

    return browse_products_list, total


async def get_filter_options(
    db: AsyncSession,
    q: str | None = None,
    category: str | None = None,
    brand: str | None = None,
    product_line: str | None = None,
    model: str | None = None,
) -> FilterOptions:
    """Get dynamically available filter values scoped to the current browse context."""

    def _apply_scoping(stmt, *, join_variant: bool = False):
        """Apply all active filters as scoping constraints."""
        if join_variant and q:
            normalized = q.strip().lower()
            stmt = stmt.where(
                or_(
                    ProductVariant.display_name.ilike(f"%{normalized}%"),
                    Product.canonical_name.ilike(f"%{normalized}%"),
                    Product.brand.ilike(f"%{normalized}%"),
                    func.coalesce(Product.product_line, "").ilike(f"%{normalized}%"),
                    func.similarity(ProductVariant.display_name, normalized) > 0.15,
                    func.similarity(Product.canonical_name, normalized) > 0.15,
                )
            )
        elif q and not join_variant:
            normalized = q.strip().lower()
            stmt = stmt.where(
                or_(
                    Product.canonical_name.ilike(f"%{normalized}%"),
                    Product.brand.ilike(f"%{normalized}%"),
                    func.coalesce(Product.product_line, "").ilike(f"%{normalized}%"),
                )
            )
        if category:
            stmt = stmt.where(Product.category == category.lower())
        if brand:
            stmt = stmt.where(func.lower(Product.brand) == brand.lower())
        if product_line:
            stmt = stmt.where(func.lower(Product.product_line) == product_line.lower())
        if model:
            stmt = stmt.where(func.lower(Product.model) == model.lower())
        return stmt

    cat_q = _apply_scoping(
        select(Product.category, func.count(func.distinct(Product.id))).group_by(Product.category)
    )
    cats = (await db.execute(cat_q)).all()
    categories = [FilterOption(value=r[0], label=r[0].title(), count=r[1]) for r in cats]

    brand_q = _apply_scoping(
        select(Product.brand, func.count(func.distinct(Product.id))).group_by(Product.brand)
    )
    brands_raw = (await db.execute(brand_q)).all()
    brands = [FilterOption(value=r[0], label=r[0], count=r[1]) for r in brands_raw]

    pl_q = _apply_scoping(
        select(Product.product_line, func.count(func.distinct(Product.id)))
        .where(Product.product_line.isnot(None))
        .group_by(Product.product_line)
    )
    pls_raw = (await db.execute(pl_q)).all()
    product_lines = [FilterOption(value=r[0], label=r[0], count=r[1]) for r in pls_raw if r[0]]

    model_q = _apply_scoping(
        select(Product.model, func.count(func.distinct(Product.id))).group_by(Product.model)
    )
    models_raw = (await db.execute(model_q)).all()
    models = [FilterOption(value=r[0], label=r[0], count=r[1]) for r in models_raw]

    storage_q = _apply_scoping(
        select(
            ProductVariant.attributes["storage"].astext.label("val"),
            func.count(ProductVariant.id),
        )
        .select_from(ProductVariant)
        .join(Product)
        .where(ProductVariant.attributes["storage"].astext.isnot(None))
        .group_by("val"),
        join_variant=True,
    )
    storages_raw = (await db.execute(storage_q)).all()
    storages = [FilterOption(value=r[0], label=r[0], count=r[1]) for r in storages_raw if r[0]]
    storages.sort(key=lambda x: _parse_storage_gb(x.value))

    color_q = _apply_scoping(
        select(
            ProductVariant.attributes["color"].astext.label("val"),
            func.count(ProductVariant.id),
        )
        .select_from(ProductVariant)
        .join(Product)
        .where(ProductVariant.attributes["color"].astext.isnot(None))
        .group_by("val"),
        join_variant=True,
    )
    colors_raw = (await db.execute(color_q)).all()
    colors = [FilterOption(value=r[0], label=r[0], count=r[1]) for r in colors_raw if r[0]]

    variant_ids_q = _apply_scoping(
        select(ProductVariant.id).select_from(ProductVariant).join(Product),
        join_variant=True,
    ).subquery()
    excluded_merchant_ids = select(Merchant.id).where(
        Merchant.slug.in_(EXCLUDED_OFFER_MERCHANT_SLUGS)
    )
    cond_q = (
        select(Offer.condition, func.count(Offer.id))
        .where(
            Offer.is_active == True,  # noqa: E712
            Offer.product_variant_id.in_(select(variant_ids_q)),
            ~Offer.merchant_id.in_(excluded_merchant_ids),
        )
        .group_by(Offer.condition)
    )
    for broken_url in EXCLUDED_OFFER_URL_SUBSTRINGS:
        cond_q = cond_q.where(~Offer.url.contains(broken_url))
    conds_raw = (await db.execute(cond_q)).all()
    conditions = [FilterOption(value=r[0], label=r[0].replace("_", " ").title(), count=r[1]) for r in conds_raw]

    price_q = (
        select(func.min(Offer.price_amount), func.max(Offer.price_amount))
        .where(
            Offer.is_active == True,  # noqa: E712
            Offer.product_variant_id.in_(select(variant_ids_q)),
            ~Offer.merchant_id.in_(excluded_merchant_ids),
        )
    )
    for broken_url in EXCLUDED_OFFER_URL_SUBSTRINGS:
        price_q = price_q.where(~Offer.url.contains(broken_url))
    price_raw = (await db.execute(price_q)).one_or_none()
    price_min = float(price_raw[0]) if price_raw and price_raw[0] else None
    price_max = float(price_raw[1]) if price_raw and price_raw[1] else None

    return FilterOptions(
        categories=categories,
        brands=brands,
        product_lines=product_lines,
        models=models,
        storages=storages,
        colors=colors,
        conditions=conditions,
        price_min=price_min,
        price_max=price_max,
    )


def _parse_storage_gb(val: str) -> int:
    val = val.upper().strip()
    match = re.match(r"(\d+)\s*(TB|GB)", val)
    if not match:
        return 0
    num = int(match.group(1))
    unit = match.group(2)
    return num * 1024 if unit == "TB" else num


async def _get_variant_offer_summary(
    db: AsyncSession, variant_id, filters: BrowseFilters
) -> dict:
    """Get offer summary for a variant: best price, count, trust, conditions."""
    excluded_merchant_ids = select(Merchant.id).where(
        Merchant.slug.in_(EXCLUDED_OFFER_MERCHANT_SLUGS)
    )
    offer_q = (
        select(Offer)
        .where(Offer.product_variant_id == variant_id, Offer.is_active == True)  # noqa: E712
        .where(~Offer.merchant_id.in_(excluded_merchant_ids))
        .options(selectinload(Offer.merchant))
    )
    for broken_url in EXCLUDED_OFFER_URL_SUBSTRINGS:
        offer_q = offer_q.where(~Offer.url.contains(broken_url))

    if filters.condition and filters.condition != "all":
        offer_q = offer_q.where(Offer.condition == filters.condition)

    if filters.mode == "high_trust":
        offer_q = offer_q.join(Merchant).where(Merchant.is_curated == True)  # noqa: E712

    result = await db.execute(offer_q)
    offers = result.scalars().all()

    if not offers:
        return {"best_price": None, "currency": None, "count": 0, "best_trust_tier": None, "conditions": []}

    best = min(offers, key=lambda o: float(o.price_amount))
    conditions = list({o.condition for o in offers})
    best_curated = any(o.merchant.is_curated for o in offers)

    return {
        "best_price": float(best.price_amount),
        "currency": best.price_currency,
        "count": len(offers),
        "best_trust_tier": "high" if best_curated else "medium",
        "conditions": conditions,
    }
