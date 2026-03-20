"""Browse & Filter API endpoints."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.browse_service import (
    BrowseFilters,
    BrowseProduct,
    FilterOption,
    FilterOptions,
    browse_products,
    get_filter_options,
)

router = APIRouter()


class BrowseProductOut(BaseModel):
    variant_id: str
    product_id: str
    display_name: str
    slug: str
    brand: str
    model: str
    category: str
    product_line: str | None = None
    attributes: dict
    image_url: str | None = None
    best_price: float | None = None
    best_price_currency: str | None = None
    offer_count: int = 0
    best_trust_tier: str | None = None
    condition_available: list[str] = []


class BrowseResponse(BaseModel):
    products: list[BrowseProductOut]
    total: int
    page: int
    per_page: int
    total_pages: int
    filters_applied: dict
    mode: str


class FilterOptionOut(BaseModel):
    value: str
    label: str
    count: int


class FilterOptionsResponse(BaseModel):
    categories: list[FilterOptionOut]
    brands: list[FilterOptionOut]
    product_lines: list[FilterOptionOut]
    models: list[FilterOptionOut]
    storages: list[FilterOptionOut]
    colors: list[FilterOptionOut]
    conditions: list[FilterOptionOut]
    price_min: float | None = None
    price_max: float | None = None


@router.get("/browse", response_model=BrowseResponse)
async def api_browse(
    q: str | None = Query(default=None, max_length=500),
    category: str | None = Query(default=None, max_length=50),
    brand: str | None = Query(default=None, max_length=100),
    product_line: str | None = Query(default=None, max_length=100),
    model: str | None = Query(default=None, max_length=200),
    storage: str | None = Query(default=None, max_length=20),
    color: str | None = Query(default=None, max_length=50),
    condition: str | None = Query(default=None, max_length=20),
    mode: str = Query(default="high_trust", max_length=20),
    sort: str = Query(default="best_deal", max_length=20),
    page: int = Query(default=1, ge=1, le=100),
    per_page: int = Query(default=24, ge=1, le=100),
    price_min: float | None = Query(default=None, ge=0),
    price_max: float | None = Query(default=None, ge=0),
    db: AsyncSession = Depends(get_db),
):
    filters = BrowseFilters(
        q=q,
        category=category,
        brand=brand,
        product_line=product_line,
        model=model,
        storage=storage,
        color=color,
        condition=condition,
        mode=mode,
        sort=sort,
        page=page,
        per_page=per_page,
        price_min=price_min,
        price_max=price_max,
    )

    products, total = await browse_products(db, filters)

    total_pages = max(1, (total + per_page - 1) // per_page)

    filters_applied = {}
    for key in ["q", "category", "brand", "product_line", "model", "storage", "color", "condition", "price_min", "price_max"]:
        val = getattr(filters, key)
        if val is not None:
            filters_applied[key] = val

    return BrowseResponse(
        products=[
            BrowseProductOut(
                variant_id=p.variant_id,
                product_id=p.product_id,
                display_name=p.display_name,
                slug=p.slug,
                brand=p.brand,
                model=p.model,
                category=p.category,
                product_line=p.product_line,
                attributes=p.attributes,
                image_url=p.image_url,
                best_price=p.best_price,
                best_price_currency=p.best_price_currency,
                offer_count=p.offer_count,
                best_trust_tier=p.best_trust_tier,
                condition_available=p.condition_available,
            )
            for p in products
        ],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        filters_applied=filters_applied,
        mode=mode,
    )


@router.get("/filters", response_model=FilterOptionsResponse)
async def api_filters(
    category: str | None = Query(default=None, max_length=50),
    db: AsyncSession = Depends(get_db),
):
    opts = await get_filter_options(db, category)

    return FilterOptionsResponse(
        categories=[FilterOptionOut(value=o.value, label=o.label, count=o.count) for o in opts.categories],
        brands=[FilterOptionOut(value=o.value, label=o.label, count=o.count) for o in opts.brands],
        product_lines=[FilterOptionOut(value=o.value, label=o.label, count=o.count) for o in opts.product_lines],
        models=[FilterOptionOut(value=o.value, label=o.label, count=o.count) for o in opts.models],
        storages=[FilterOptionOut(value=o.value, label=o.label, count=o.count) for o in opts.storages],
        colors=[FilterOptionOut(value=o.value, label=o.label, count=o.count) for o in opts.colors],
        conditions=[FilterOptionOut(value=o.value, label=o.label, count=o.count) for o in opts.conditions],
        price_min=opts.price_min,
        price_max=opts.price_max,
    )
