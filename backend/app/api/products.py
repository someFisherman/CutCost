"""Product & Offer API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.merchant import Merchant
from app.offer_visibility import (
    EXCLUDED_OFFER_MERCHANT_SLUGS,
    EXCLUDED_OFFER_URL_SUBSTRINGS,
)
from app.models.offer import Offer
from app.models.product import Product, ProductVariant
from app.models.trust import TrustScore
from app.services.cost_service import TotalCostBreakdown, calculate_total_cost
from app.services.affiliate_service import build_affiliate_url
from app.services.ranking_service import OfferForRanking, RankedOffer, rank_offers

router = APIRouter()


class CostComponentOut(BaseModel):
    value: float
    currency: str
    source: str
    note: str = ""


class CostBreakdownOut(BaseModel):
    base_price: CostComponentOut
    shipping: CostComponentOut
    import_vat: CostComponentOut
    customs_fee: CostComponentOut
    import_duty: CostComponentOut
    total: float
    total_low: float | None = None
    total_high: float | None = None
    currency: str
    confidence: str


class MerchantOut(BaseModel):
    name: str
    slug: str
    country: str
    logo_url: str | None = None
    trust_score: float
    trust_tier: str


class OfferOut(BaseModel):
    id: str
    merchant: MerchantOut
    price: float
    price_currency: str
    total_cost: CostBreakdownOut
    condition: str
    availability: str
    delivery_days_min: int | None = None
    delivery_days_max: int | None = None
    match_confidence: float | None = None
    mismatch_flags: list[dict] = []
    url: str
    affiliate_url: str | None = None
    is_affiliate: bool = False
    rank: int
    label: str | None = None
    explanation: str


class ProductDetailOut(BaseModel):
    id: str
    brand: str
    model: str
    canonical_name: str
    category: str
    image_url: str | None = None
    slug: str


class VariantDetailOut(BaseModel):
    id: str
    display_name: str
    slug: str
    attributes: dict
    image_url: str | None = None


class ProductOffersResponse(BaseModel):
    product: ProductDetailOut
    variant: VariantDetailOut
    offers: list[OfferOut]
    meta: dict


class BlockOfferUrlRequest(BaseModel):
    url: str


class BlockOfferUrlResponse(BaseModel):
    blocked_count: int
    message: str
    action: str = "blocked"


@router.get("/products/{slug}/offers", response_model=ProductOffersResponse)
async def get_product_offers(
    slug: str,
    country: str = Query(default=settings.default_buyer_country, max_length=2),
    condition: str = Query(default="all", max_length=20),
    sort: str = Query(default="best_deal", max_length=20),
    mode: str = Query(default="high_trust", max_length=20),
    db: AsyncSession = Depends(get_db),
):
    variant_result = await db.execute(
        select(ProductVariant)
        .where(ProductVariant.slug == slug)
        .options(selectinload(ProductVariant.product))
    )
    variant = variant_result.scalar_one_or_none()

    if not variant:
        raise HTTPException(status_code=404, detail="Product not found")

    excluded_merchant_ids = select(Merchant.id).where(
        Merchant.slug.in_(EXCLUDED_OFFER_MERCHANT_SLUGS)
    )
    offer_query = (
        select(Offer)
        .where(Offer.product_variant_id == variant.id)
        .where(Offer.is_active == True)  # noqa: E712
        .where(~Offer.merchant_id.in_(excluded_merchant_ids))
        .options(selectinload(Offer.merchant))
    )
    for broken_url in EXCLUDED_OFFER_URL_SUBSTRINGS:
        offer_query = offer_query.where(~Offer.url.contains(broken_url))
    if condition != "all":
        offer_query = offer_query.where(Offer.condition == condition)
    if mode == "high_trust":
        offer_query = offer_query.join(Merchant).where(Merchant.is_curated == True)  # noqa: E712

    offer_result = await db.execute(offer_query)
    offers = offer_result.scalars().all()

    buyer_currency = settings.default_currency
    offers_for_ranking: list[OfferForRanking] = []

    for offer in offers:
        merchant = offer.merchant

        trust = await _get_merchant_trust(db, merchant.id)
        trust_score_val = float(trust.overall_score) if trust else (0.85 if merchant.is_curated else 0.30)
        trust_tier_val = trust.tier if trust else ("high" if merchant.is_curated else "low")
        red_flags_val = trust.red_flags if trust else []

        cost = await calculate_total_cost(
            db=db,
            price_amount=float(offer.price_amount),
            price_currency=offer.price_currency,
            merchant=merchant,
            buyer_country=country,
            buyer_currency=buyer_currency,
            category=variant.product.category,
            offer_shipping_cost=float(offer.shipping_cost) if offer.shipping_cost else None,
            offer_shipping_currency=offer.shipping_currency,
        )

        delivery = offer.delivery_days_min or offer.delivery_days_max
        offers_for_ranking.append(OfferForRanking(
            offer_id=str(offer.id),
            total_cost=cost.total,
            trust_score=trust_score_val,
            trust_tier=trust_tier_val,
            delivery_days=delivery,
            condition=offer.condition,
            match_confidence=float(offer.match_confidence) if offer.match_confidence else 0.5,
            merchant_name=merchant.name,
            merchant_country=merchant.country,
            is_domestic=merchant.country == country,
            red_flags=red_flags_val,
            cost_breakdown=cost,
        ))

    ranked = rank_offers(offers_for_ranking, buyer_currency, sort=sort)

    offer_map = {str(o.id): o for o in offers}
    merchant_map = {str(o.merchant.id): o.merchant for o in offers}
    ranking_map = {r.offer_id: r for r in ranked}

    offer_outputs: list[OfferOut] = []
    for r in ranked:
        offer = offer_map[r.offer_id]
        merchant = offer.merchant
        trust = await _get_merchant_trust(db, merchant.id)
        trust_score_val = float(trust.overall_score) if trust else (0.85 if merchant.is_curated else 0.30)
        trust_tier_val = trust.tier if trust else ("high" if merchant.is_curated else "low")

        cost_out = _cost_to_out(r.total_cost)

        effective_affiliate_url = offer.affiliate_url or build_affiliate_url(
            offer.url, merchant.slug
        )

        offer_outputs.append(OfferOut(
            id=str(offer.id),
            merchant=MerchantOut(
                name=merchant.name,
                slug=merchant.slug,
                country=merchant.country,
                logo_url=merchant.logo_url,
                trust_score=trust_score_val,
                trust_tier=trust_tier_val,
            ),
            price=float(offer.price_amount),
            price_currency=offer.price_currency,
            total_cost=cost_out,
            condition=offer.condition,
            availability=offer.availability,
            delivery_days_min=offer.delivery_days_min,
            delivery_days_max=offer.delivery_days_max,
            match_confidence=float(offer.match_confidence) if offer.match_confidence else None,
            mismatch_flags=offer.mismatch_flags,
            url=offer.url,
            affiliate_url=effective_affiliate_url,
            is_affiliate=effective_affiliate_url is not None,
            rank=r.rank,
            label=r.label,
            explanation=r.explanation,
        ))

    return ProductOffersResponse(
        product=ProductDetailOut(
            id=str(variant.product.id),
            brand=variant.product.brand,
            model=variant.product.model,
            canonical_name=variant.product.canonical_name,
            category=variant.product.category,
            image_url=variant.product.image_url,
            slug=variant.product.slug,
        ),
        variant=VariantDetailOut(
            id=str(variant.id),
            display_name=variant.display_name,
            slug=variant.slug,
            attributes=variant.attributes,
            image_url=variant.image_url,
        ),
        offers=offer_outputs,
        meta={
            "total_offers": len(offer_outputs),
            "buyer_country": country,
            "buyer_currency": buyer_currency,
            "sort": sort,
            "mode": mode,
            "disclaimer": "Prices are estimates. Actual cost may vary at checkout.",
        },
    )


async def _get_merchant_trust(db: AsyncSession, merchant_id) -> TrustScore | None:
    result = await db.execute(
        select(TrustScore)
        .where(TrustScore.merchant_id == merchant_id)
        .order_by(TrustScore.computed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _cost_to_out(cost: TotalCostBreakdown) -> CostBreakdownOut:
    return CostBreakdownOut(
        base_price=CostComponentOut(
            value=cost.base_price.value, currency=cost.base_price.currency,
            source=cost.base_price.source, note=cost.base_price.note,
        ),
        shipping=CostComponentOut(
            value=cost.shipping.value, currency=cost.shipping.currency,
            source=cost.shipping.source, note=cost.shipping.note,
        ),
        import_vat=CostComponentOut(
            value=cost.import_vat.value, currency=cost.import_vat.currency,
            source=cost.import_vat.source, note=cost.import_vat.note,
        ),
        customs_fee=CostComponentOut(
            value=cost.customs_fee.value, currency=cost.customs_fee.currency,
            source=cost.customs_fee.source, note=cost.customs_fee.note,
        ),
        import_duty=CostComponentOut(
            value=cost.import_duty.value, currency=cost.import_duty.currency,
            source=cost.import_duty.source, note=cost.import_duty.note,
        ),
        total=cost.total,
        total_low=cost.total_low,
        total_high=cost.total_high,
        currency=cost.currency,
        confidence=cost.confidence,
    )


@router.post("/offers/block-url", response_model=BlockOfferUrlResponse)
async def block_offer_url(
    payload: BlockOfferUrlRequest,
    db: AsyncSession = Depends(get_db),
):
    target_url = payload.url.strip()
    if not target_url:
        return BlockOfferUrlResponse(blocked_count=0, message="No URL provided")

    should_disable = False
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            head = await client.head(target_url)
            status = head.status_code
            if status == 405:
                get_resp = await client.get(target_url)
                status = get_resp.status_code
            should_disable = status >= 400
    except Exception:
        # Network failures are treated as unreliable URL checks.
        should_disable = False

    if should_disable:
        res = await db.execute(
            update(Offer)
            .where(Offer.url == target_url, Offer.is_active == True)  # noqa: E712
            .values(is_active=False)
        )
        await db.commit()
        blocked = res.rowcount or 0
        return BlockOfferUrlResponse(
            blocked_count=blocked,
            message=f"Blocked {blocked} offer(s): URL returned HTTP error",
            action="blocked",
        )

    res = await db.execute(
        update(Offer)
        .where(Offer.url == target_url)
        .values(review_status="pending")
    )
    await db.commit()
    blocked = res.rowcount or 0
    return BlockOfferUrlResponse(
        blocked_count=blocked,
        message=f"Flagged {blocked} offer(s) for manual review (URL reachable)",
        action="flagged",
    )
