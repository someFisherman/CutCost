"""Add offers to the database from various sources.

This script adds curated offers for products across multiple merchants.
For MVP: manually researched prices. Later: automated extraction.

Usage: python add_offers.py
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
from app.models.merchant import Merchant
from app.models.offer import Offer, OfferPriceSnapshot
from app.models.product import Product, ProductVariant

CURATED_OFFERS = [
    {
        "product_line": "iPhone", "model": "16 Pro", "variant_key": "256gb-natural-titanium",
        "offers": [
            {"merchant": "amazon-de", "price": 1149.00, "currency": "EUR", "condition": "new",
             "url": "https://www.amazon.de/dp/B0DGWRCQFX", "delivery_min": 3, "delivery_max": 5},
            {"merchant": "interdiscount-ch", "price": 1129.00, "currency": "CHF", "condition": "new",
             "url": "https://www.interdiscount.ch/de/apple-iphone-16-pro-256gb-natural-titanium", "delivery_min": 1, "delivery_max": 3},
            {"merchant": "backmarket-ch", "price": 899.00, "currency": "CHF", "condition": "refurbished",
             "url": "https://www.backmarket.ch/de-ch/p/iphone-16-pro-256-gb-natural-titanium/refurbished", "delivery_min": 3, "delivery_max": 7},
        ],
    },
    {
        "product_line": "iPhone", "model": "16 Pro", "variant_key": "256gb-black-titanium",
        "offers": [
            {"merchant": "amazon-de", "price": 1149.00, "currency": "EUR", "condition": "new",
             "url": "https://www.amazon.de/dp/B0DGWT1LXL", "delivery_min": 3, "delivery_max": 5},
            {"merchant": "interdiscount-ch", "price": 1129.00, "currency": "CHF", "condition": "new",
             "url": "https://www.interdiscount.ch/de/apple-iphone-16-pro-256gb-black-titanium", "delivery_min": 1, "delivery_max": 3},
        ],
    },
    {
        "product_line": "iPhone", "model": "15 Pro", "variant_key": "256gb-black-titanium",
        "offers": [
            {"merchant": "amazon-de", "price": 949.00, "currency": "EUR", "condition": "new",
             "url": "https://www.amazon.de/dp/B0CMZ4D4XF", "delivery_min": 3, "delivery_max": 5},
            {"merchant": "backmarket-ch", "price": 679.00, "currency": "CHF", "condition": "refurbished",
             "url": "https://www.backmarket.ch/de-ch/p/iphone-15-pro-256-gb-black-titanium/refurbished", "delivery_min": 3, "delivery_max": 7},
        ],
    },
    {
        "product_line": "Galaxy", "model": "S25 Ultra", "variant_key": "256gb-titanium-black",
        "offers": [
            {"merchant": "amazon-de", "price": 1299.00, "currency": "EUR", "condition": "new",
             "url": "https://www.amazon.de/dp/B0DS1VGD3V", "delivery_min": 3, "delivery_max": 5},
            {"merchant": "interdiscount-ch", "price": 1399.00, "currency": "CHF", "condition": "new",
             "url": "https://www.interdiscount.ch/de/samsung-galaxy-s25-ultra-256gb-titanium-black", "delivery_min": 1, "delivery_max": 3},
        ],
    },
    {
        "product_line": "Galaxy", "model": "S24 Ultra", "variant_key": "256gb-titanium-black",
        "offers": [
            {"merchant": "amazon-de", "price": 999.00, "currency": "EUR", "condition": "new",
             "url": "https://www.amazon.de/dp/B0CS5K4CD2", "delivery_min": 3, "delivery_max": 5},
            {"merchant": "backmarket-ch", "price": 749.00, "currency": "CHF", "condition": "refurbished",
             "url": "https://www.backmarket.ch/de-ch/p/samsung-galaxy-s24-ultra-256gb/refurbished", "delivery_min": 3, "delivery_max": 7},
        ],
    },
    {
        "product_line": "Pixel", "model": "9 Pro", "variant_key": "128gb-obsidian",
        "offers": [
            {"merchant": "amazon-de", "price": 799.00, "currency": "EUR", "condition": "new",
             "url": "https://www.amazon.de/dp/B0D7JRZF9X", "delivery_min": 3, "delivery_max": 5},
            {"merchant": "interdiscount-ch", "price": 1049.00, "currency": "CHF", "condition": "new",
             "url": "https://www.interdiscount.ch/de/google-pixel-9-pro-128gb-obsidian", "delivery_min": 2, "delivery_max": 4},
        ],
    },
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
    now = datetime.now(timezone.utc)
    total = 0

    async with async_session() as session:
        merchant_cache: dict[str, Merchant] = {}

        for product_def in CURATED_OFFERS:
            pl = product_def["product_line"]
            model = product_def["model"]
            vk = product_def["variant_key"]

            variant = await find_variant(session, pl, model, vk)
            if not variant:
                print(f"SKIP: {pl} {model} ({vk}) — variant not in DB")
                continue

            print(f"\n--- {pl} {model} ({vk}) ---")

            for offer_def in product_def["offers"]:
                merchant_slug = offer_def["merchant"]
                if merchant_slug not in merchant_cache:
                    m = await find_merchant(session, merchant_slug)
                    if not m:
                        print(f"  SKIP: Merchant '{merchant_slug}' not in DB")
                        continue
                    merchant_cache[merchant_slug] = m
                merchant = merchant_cache[merchant_slug]

                url = offer_def["url"]
                existing = await session.execute(
                    select(Offer).where(Offer.url == url)
                )
                existing_offer = existing.scalar_one_or_none()

                if existing_offer:
                    existing_offer.price_amount = offer_def["price"]
                    existing_offer.price_currency = offer_def["currency"]
                    existing_offer.condition = offer_def["condition"]
                    existing_offer.last_checked = now
                    existing_offer.check_count += 1
                    offer = existing_offer
                    action = "UPD"
                else:
                    offer = Offer(
                        id=uuid4(),
                        product_variant_id=variant.id,
                        merchant_id=merchant.id,
                        url=url,
                        raw_title=f"{pl} {model} ({vk})",
                        extracted_attributes={"source": "curated"},
                        identifiers_found=[],
                        price_amount=offer_def["price"],
                        price_currency=offer_def["currency"],
                        shipping_cost=0.0,
                        shipping_currency=offer_def["currency"],
                        shipping_source="curated",
                        condition=offer_def["condition"],
                        availability="in_stock",
                        delivery_days_min=offer_def.get("delivery_min"),
                        delivery_days_max=offer_def.get("delivery_max"),
                        match_confidence=0.90,
                        match_method="curated_manual",
                        match_reasons=["manual_price_entry"],
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
                    price_amount=offer_def["price"],
                    price_currency=offer_def["currency"],
                    observed_at=now,
                )
                session.add(snapshot)
                total += 1
                print(f"  [{action}] {merchant.name}: {offer_def['price']} {offer_def['currency']} ({offer_def['condition']})")

        await session.commit()
        print(f"\nDone — {total} offers added/updated.")


if __name__ == "__main__":
    asyncio.run(main())
