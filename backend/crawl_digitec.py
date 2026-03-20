"""Crawl Digitec for real offers and store them in the database.

Usage: python crawl_digitec.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from uuid import uuid4

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.extractors.digitec import DigitecExtractor
from app.models.merchant import Merchant
from app.models.offer import Offer, OfferPriceSnapshot
from app.models.product import Product, ProductVariant


DIGITEC_PRODUCTS = [
    (49221237, "256gb-natural-titanium", "iPhone", "16 Pro"),
    (38606712, "256gb-black-titanium", "iPhone", "15 Pro"),
    (41969659, "256gb-titanium-black", "Galaxy", "S24 Ultra"),
]


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
    result = await session.execute(
        select(Merchant).where(Merchant.slug == slug)
    )
    return result.scalar_one_or_none()


async def main():
    extractor = DigitecExtractor(lang="de")
    now = datetime.now(timezone.utc)
    total_offers = 0

    async with async_session() as session:
        merchant = await find_merchant(session, "digitec-ch")
        if not merchant:
            print("ERROR: Merchant 'digitec-ch' not found. Run seed first.")
            return

        for digitec_id, variant_key, product_line, model in DIGITEC_PRODUCTS:
            print(f"\n--- Digitec #{digitec_id}: {product_line} {model} ({variant_key}) ---")

            variant = await find_variant(session, product_line, model, variant_key)
            if not variant:
                print(f"  SKIP: Variant '{variant_key}' not found in DB")
                continue

            try:
                extracted = await extractor.extract_offers_by_id(digitec_id)
            except Exception as e:
                print(f"  ERROR: {e}")
                continue

            print(f"  {len(extracted)} offers found")

            for ext_offer in extracted:
                offer_id_str = ext_offer.extracted_attributes.get("offer_id", "")
                offer_url = f"{ext_offer.product_url}?offerId={offer_id_str}"

                existing = await session.execute(
                    select(Offer).where(Offer.url == offer_url)
                )
                existing_offer = existing.scalar_one_or_none()

                if existing_offer:
                    existing_offer.price_amount = ext_offer.price_amount
                    existing_offer.price_currency = ext_offer.price_currency
                    existing_offer.availability = ext_offer.availability
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
                        match_confidence=0.95,
                        match_method="curated_mapping",
                        match_reasons=["digitec_product_id_mapping"],
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
                total_offers += 1

                offer_type = ext_offer.extracted_attributes.get("offer_type", "?")
                print(f"  [{action}] {ext_offer.price_amount} {ext_offer.price_currency} ({ext_offer.condition}/{offer_type})")

        await session.commit()
        print(f"\nDone — {total_offers} offers stored.")


if __name__ == "__main__":
    asyncio.run(main())
