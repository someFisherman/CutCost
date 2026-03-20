"""Crawl Digitec/Galaxus product IDs from mapping file and store offers.

Usage: python crawl_digitec.py
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.extractors.digitec import DigitecExtractor, GalaxusExtractor
from app.models.merchant import Merchant
from app.models.offer import Offer, OfferPriceSnapshot
from app.models.product import Product, ProductVariant

MAPPINGS_PATH = Path(__file__).parent / "seeds" / "digitec_mappings.json"


async def find_variant(session: AsyncSession, product_line: str, model: str, variant_key: str):
    result = await session.execute(
        select(ProductVariant)
        .join(Product)
        .where(
            Product.product_line == product_line,
            Product.model == model,
            ProductVariant.variant_key == variant_key,
        )
    )
    return result.scalar_one_or_none()


async def find_merchant(session: AsyncSession, slug: str):
    result = await session.execute(select(Merchant).where(Merchant.slug == slug))
    return result.scalar_one_or_none()


def load_jobs() -> list[dict]:
    raw = json.loads(MAPPINGS_PATH.read_text(encoding="utf-8"))
    jobs: list[dict] = []
    for merchant_slug, items in raw.items():
        for item in items:
            jobs.append(
                {
                    "merchant_slug": merchant_slug,
                    "product_id": int(item["digitec_id"]),
                    "variant_key": item["variant_key"],
                    "product_line": item["product_line"],
                    "model": item["model"],
                }
            )
    return jobs


def get_extractor(merchant_slug: str):
    if merchant_slug == "galaxus-ch":
        return GalaxusExtractor(lang="de")
    return DigitecExtractor(lang="de")


async def upsert_offer(
    session: AsyncSession,
    variant: ProductVariant,
    merchant: Merchant,
    ext_offer,
    now: datetime,
):
    offer_url = ext_offer.product_url
    existing = await session.execute(select(Offer).where(Offer.url == offer_url))
    existing_offer = existing.scalar_one_or_none()

    if existing_offer:
        existing_offer.price_amount = ext_offer.price_amount
        existing_offer.price_currency = ext_offer.price_currency
        existing_offer.availability = ext_offer.availability
        existing_offer.shipping_cost = ext_offer.shipping_cost
        existing_offer.shipping_currency = ext_offer.shipping_currency or "CHF"
        existing_offer.condition = ext_offer.condition
        existing_offer.delivery_days_min = ext_offer.delivery_days_min
        existing_offer.delivery_days_max = ext_offer.delivery_days_max
        existing_offer.extracted_attributes = ext_offer.extracted_attributes
        existing_offer.is_active = True
        existing_offer.last_checked = now
        existing_offer.check_count += 1
        offer = existing_offer
        action = "UPD"
    else:
        offer = Offer(
            id=uuid4(),
            product_variant_id=variant.id,
            merchant_id=merchant.id,
            url=offer_url,
            raw_title=ext_offer.raw_title,
            extracted_attributes=ext_offer.extracted_attributes,
            identifiers_found=[],
            price_amount=ext_offer.price_amount,
            price_currency=ext_offer.price_currency,
            shipping_cost=ext_offer.shipping_cost,
            shipping_currency=ext_offer.shipping_currency or "CHF",
            shipping_source="curated",
            condition=ext_offer.condition,
            availability=ext_offer.availability,
            delivery_days_min=ext_offer.delivery_days_min,
            delivery_days_max=ext_offer.delivery_days_max,
            match_confidence=0.95,
            match_method="curated_mapping",
            match_reasons=["merchant_product_id_mapping"],
            mismatch_flags=[],
            review_status="auto_approved",
            is_active=True,
            last_checked=now,
            check_count=1,
        )
        session.add(offer)
        action = "NEW"

    snapshot = OfferPriceSnapshot(
        id=uuid4(),
        offer_id=offer.id,
        price_amount=ext_offer.price_amount,
        price_currency=ext_offer.price_currency,
        observed_at=now,
    )
    session.add(snapshot)
    return action


async def main():
    now = datetime.now(timezone.utc)
    jobs = load_jobs()
    total_offers = 0

    async with async_session() as session:
        for job in jobs:
            merchant_slug = job["merchant_slug"]
            merchant = await find_merchant(session, merchant_slug)
            if not merchant:
                print(f"SKIP: merchant not found: {merchant_slug}")
                continue

            variant = await find_variant(
                session,
                job["product_line"],
                job["model"],
                job["variant_key"],
            )
            if not variant:
                print(
                    f"SKIP: variant not found for {job['product_line']} {job['model']} {job['variant_key']}"
                )
                continue

            extractor = get_extractor(merchant_slug)
            product_id = job["product_id"]
            print(
                f"\n--- {merchant_slug} #{product_id}: {job['product_line']} {job['model']} ({job['variant_key']}) ---"
            )

            try:
                extracted = await extractor.extract_offers_by_id(product_id)
            except Exception as e:
                print(f"  ERROR: {e}")
                continue

            print(f"  {len(extracted)} offers found")
            for ext_offer in extracted:
                action = await upsert_offer(session, variant, merchant, ext_offer, now)
                total_offers += 1
                offer_type = ext_offer.extracted_attributes.get("offer_type", "?")
                print(
                    f"  [{action}] {ext_offer.price_amount} {ext_offer.price_currency} ({ext_offer.condition}/{offer_type})"
                )

        await session.commit()
        print(f"\nDone — {total_offers} offers stored.")


if __name__ == "__main__":
    asyncio.run(main())
