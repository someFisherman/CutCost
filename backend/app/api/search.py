"""Search API endpoints."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.search_service import autocomplete, search_products

router = APIRouter()


class AutocompleteItem(BaseModel):
    variant_id: str
    product_id: str
    display_name: str
    slug: str
    category: str
    brand: str
    image_url: str | None


class AutocompleteResponse(BaseModel):
    suggestions: list[AutocompleteItem]


class VariantSummary(BaseModel):
    id: str
    display_name: str
    slug: str
    attributes: dict
    image_url: str | None


class ProductSummary(BaseModel):
    id: str
    brand: str
    model: str
    canonical_name: str
    category: str
    image_url: str | None


class SearchResponse(BaseModel):
    query: str
    type: str  # "exact", "disambiguation", "multiple", "empty"
    matched_variant: VariantSummary | None = None
    matched_product: ProductSummary | None = None
    variants: list[VariantSummary] = []
    redirect_to: str | None = None


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def api_autocomplete(
    q: str = Query(..., min_length=2, max_length=200),
    db: AsyncSession = Depends(get_db),
):
    suggestions = await autocomplete(db, q)
    return AutocompleteResponse(suggestions=[AutocompleteItem(**s) for s in suggestions])


@router.get("/search", response_model=SearchResponse)
async def api_search(
    q: str = Query(..., min_length=1, max_length=500),
    country: str = Query(default=settings.default_buyer_country, max_length=2),
    db: AsyncSession = Depends(get_db),
):
    result = await search_products(db, q)

    response = SearchResponse(query=q, type=result["type"])

    if result["type"] == "exact" and result["variant"]:
        v = result["variant"]
        response.matched_variant = VariantSummary(
            id=str(v.id),
            display_name=v.display_name,
            slug=v.slug,
            attributes=v.attributes,
            image_url=v.image_url,
        )
        response.matched_product = ProductSummary(
            id=str(v.product.id),
            brand=v.product.brand,
            model=v.product.model,
            canonical_name=v.product.canonical_name,
            category=v.product.category,
            image_url=v.product.image_url,
        )
        response.redirect_to = f"/product/{v.slug}"

    if result["variants"]:
        response.variants = [
            VariantSummary(
                id=str(v.id),
                display_name=v.display_name,
                slug=v.slug,
                attributes=v.attributes,
                image_url=v.image_url or (v.product.image_url if v.product else None),
            )
            for v in result["variants"]
        ]

    return response
