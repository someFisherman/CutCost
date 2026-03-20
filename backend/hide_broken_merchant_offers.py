"""Deactivate offers from merchants with known-broken product URLs (optional DB cleanup).

API already hides these via app.offer_visibility — this script marks rows inactive
so crawlers/admin views stay consistent. Run once against production if desired:

    python hide_broken_merchant_offers.py
"""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text

from app.database import async_session
from app.offer_visibility import (
    EXCLUDED_OFFER_MERCHANT_SLUGS,
    EXCLUDED_OFFER_URL_SUBSTRINGS,
)


async def main():
    async with async_session() as db:
        total = 0
        for slug in EXCLUDED_OFFER_MERCHANT_SLUGS:
            r = await db.execute(
                text("""
                    UPDATE offer o
                    SET is_active = false
                    FROM merchant m
                    WHERE o.merchant_id = m.id AND m.slug = :slug AND o.is_active = true
                """),
                {"slug": slug},
            )
            total += r.rowcount or 0
        for bad_url in EXCLUDED_OFFER_URL_SUBSTRINGS:
            r = await db.execute(
                text("""
                    UPDATE offer
                    SET is_active = false
                    WHERE url LIKE :bad_url AND is_active = true
                """),
                {"bad_url": f"%{bad_url}%"},
            )
            total += r.rowcount or 0
        await db.commit()
        print(
            f"Deactivated {total} offer(s) for merchant/url exclusions. "
            f"Merchants={sorted(EXCLUDED_OFFER_MERCHANT_SLUGS)} "
            f"URLs={list(EXCLUDED_OFFER_URL_SUBSTRINGS)}"
        )


if __name__ == "__main__":
    asyncio.run(main())
