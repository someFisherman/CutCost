"""Search API endpoints."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.deep_search_service import (
    deep_search_job_to_dict,
    get_deep_search_job,
    start_deep_search,
)
from app.services.search_service import autocomplete, parse_query_to_filters, search_products

router = APIRouter()


class AutocompleteItem(BaseModel):
    variant_id: str
    product_id: str
    display_name: str
    slug: str
    category: str
    brand: str
    image_url: str | None
    type: str = "variant"
    filter_url: str | None = None


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


class ParsedQueryOut(BaseModel):
    brand: str | None = None
    product_line: str | None = None
    model: str | None = None
    storage: str | None = None
    color: str | None = None
    has_filters: bool = False


class SearchResponse(BaseModel):
    query: str
    type: str  # "exact", "disambiguation", "multiple", "browse_redirect", "empty"
    matched_variant: VariantSummary | None = None
    matched_product: ProductSummary | None = None
    variants: list[VariantSummary] = []
    redirect_to: str | None = None
    parsed_query: ParsedQueryOut | None = None


class DeepSearchStartResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str


class DeepSearchStatusResponse(BaseModel):
    id: str
    query: str
    status: str
    progress: int
    scanned_products: int
    total_products: int
    offers_upserted: int
    started_at: str
    completed_at: str | None = None
    message: str
    error: str | None = None
    source_errors: int = 0
    error_samples: list[str] = Field(default_factory=list)


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
    parsed = result.get("parsed")

    parsed_out = None
    if parsed:
        parsed_out = ParsedQueryOut(
            brand=parsed.brand,
            product_line=parsed.product_line,
            model=parsed.model,
            storage=parsed.storage,
            color=parsed.color,
            has_filters=parsed.has_filters,
        )

    response = SearchResponse(query=q, type=result["type"], parsed_query=parsed_out)

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

    if result["type"] == "browse_redirect" and parsed and parsed.has_filters:
        params = []
        if parsed.brand:
            params.append(f"brand={parsed.brand}")
        if parsed.product_line:
            params.append(f"product_line={parsed.product_line}")
        if parsed.model:
            params.append(f"model={parsed.model}")
        if parsed.storage:
            params.append(f"storage={parsed.storage}")
        if parsed.color:
            params.append(f"color={parsed.color}")
        response.redirect_to = "/browse?" + "&".join(params)

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

    if result["type"] == "multiple" and parsed and parsed.has_filters:
        params = ["q=" + q]
        if parsed.brand:
            params.append(f"brand={parsed.brand}")
        if parsed.product_line:
            params.append(f"product_line={parsed.product_line}")
        response.redirect_to = "/browse?" + "&".join(params)

    return response


@router.get("/parse-query", response_model=ParsedQueryOut)
async def api_parse_query(
    q: str = Query(..., min_length=1, max_length=500),
):
    """Debug/utility endpoint: parse a query string into structured filters."""
    parsed = parse_query_to_filters(q)
    return ParsedQueryOut(
        brand=parsed.brand,
        product_line=parsed.product_line,
        model=parsed.model,
        storage=parsed.storage,
        color=parsed.color,
        has_filters=parsed.has_filters,
    )


@router.post("/deep-search/start", response_model=DeepSearchStartResponse)
async def api_start_deep_search(
    q: str = Query(..., min_length=2, max_length=500),
):
    job = await start_deep_search(q)
    return DeepSearchStartResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        message=job.message,
    )


@router.get("/deep-search/{job_id}", response_model=DeepSearchStatusResponse)
async def api_get_deep_search(job_id: str):
    job = await get_deep_search_job(job_id)
    if not job:
        return DeepSearchStatusResponse(
            id=job_id,
            query="",
            status="not_found",
            progress=0,
            scanned_products=0,
            total_products=0,
            offers_upserted=0,
            started_at="",
            completed_at=None,
            message="Deep search job not found",
            error=None,
        )
    return DeepSearchStatusResponse(**deep_search_job_to_dict(job))
