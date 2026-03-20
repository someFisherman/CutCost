"""Seed the database with initial products, merchants, and import rules."""

import asyncio
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.database import async_session, engine
from app.models import Base
from app.models.cost import CurrencyRate, ImportRule
from app.models.merchant import Merchant, MerchantDomain, MerchantShippingRule
from app.models.product import Product, ProductIdentifier, ProductSearchAlias, ProductVariant
from app.models.trust import TrustScore
from app.utils.normalization import slugify

SEEDS_DIR = Path(__file__).parent


async def seed_products(session):
    data = json.loads((SEEDS_DIR / "products.json").read_text(encoding="utf-8"))
    count = 0

    for p in data:
        product_slug = slugify(p["canonical_name"])
        product = Product(
            category=p["category"],
            brand=p["brand"],
            product_line=p.get("product_line"),
            model=p["model"],
            canonical_name=p["canonical_name"],
            short_name=f"{p['brand']} {p['model']}",
            slug=product_slug,
            release_date=date.fromisoformat(p["release_date"]) if p.get("release_date") else None,
        )
        session.add(product)
        await session.flush()

        for v in p.get("variants", []):
            variant_slug = slugify(v["display_name"])
            variant = ProductVariant(
                product_id=product.id,
                variant_key=v["variant_key"],
                display_name=v["display_name"],
                slug=variant_slug,
                attributes=v.get("attributes", {}),
                is_default=v.get("is_default", False),
            )
            session.add(variant)
            await session.flush()

            for ident in v.get("identifiers", []):
                session.add(ProductIdentifier(
                    variant_id=variant.id,
                    identifier_type=ident["type"],
                    value=ident["value"],
                    region=ident.get("region"),
                ))

            # Auto-generate search aliases
            alias_texts = [
                v["display_name"].lower(),
                f"{p['brand']} {p['model']} {v['attributes'].get('storage', '')}".strip().lower(),
            ]
            for alias_text in alias_texts:
                session.add(ProductSearchAlias(
                    variant_id=variant.id,
                    product_id=product.id,
                    alias=alias_text,
                ))

            count += 1

    await session.commit()
    print(f"  Seeded {count} product variants")


async def seed_merchants(session):
    data = json.loads((SEEDS_DIR / "merchants.json").read_text(encoding="utf-8"))
    count = 0

    for m in data:
        merchant = Merchant(
            slug=m["slug"],
            name=m["name"],
            website=m["website"],
            country=m["country"],
            currency=m["currency"],
            is_marketplace=m.get("is_marketplace", False),
            is_curated=m.get("is_curated", False),
            affiliate_config=m.get("affiliate_config", {}),
            notes=m.get("notes"),
        )
        session.add(merchant)
        await session.flush()

        for d in m.get("domains", []):
            session.add(MerchantDomain(
                merchant_id=merchant.id,
                domain=d["domain"],
                is_primary=d.get("is_primary", False),
                whois_created=date.fromisoformat(d["whois_created"]) if d.get("whois_created") else None,
                has_https=d.get("has_https", True),
            ))

        for s in m.get("shipping", []):
            session.add(MerchantShippingRule(
                merchant_id=merchant.id,
                destination_country=s["destination_country"],
                cost_amount=s.get("cost_amount"),
                cost_currency=s.get("cost_currency", "CHF"),
                free_above=s.get("free_above"),
                estimated_days_min=s.get("estimated_days_min"),
                estimated_days_max=s.get("estimated_days_max"),
                source=s.get("source", "curated"),
                notes=s.get("notes"),
            ))

        # Auto-create trust score for curated merchants
        if m.get("is_curated"):
            session.add(TrustScore(
                merchant_id=merchant.id,
                overall_score=0.85,
                tier="high",
                signal_breakdown={"curated": 1.0},
                red_flags=[],
                is_override=True,
                override_reason="Manually curated merchant",
                expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            ))

        count += 1

    await session.commit()
    print(f"  Seeded {count} merchants")


async def seed_import_rules(session):
    data = json.loads((SEEDS_DIR / "import_rules.json").read_text(encoding="utf-8"))
    count = 0

    for r in data:
        session.add(ImportRule(
            buyer_country=r["buyer_country"],
            product_category=r.get("product_category"),
            duty_rate=r["duty_rate"],
            vat_rate=r["vat_rate"],
            de_minimis_amount=r.get("de_minimis_amount"),
            de_minimis_currency=r.get("de_minimis_currency"),
            customs_fee=r.get("customs_fee", 0),
            notes=r.get("notes"),
            valid_from=date.fromisoformat(r["valid_from"]),
        ))
        count += 1

    await session.commit()
    print(f"  Seeded {count} import rules")


async def seed_currency_rates(session):
    now = datetime.now(timezone.utc)
    rates = [
        ("EUR", "CHF", 0.9650),
        ("USD", "CHF", 0.8850),
        ("GBP", "CHF", 1.1200),
        ("EUR", "USD", 1.0900),
        ("EUR", "GBP", 0.8600),
    ]
    for from_cur, to_cur, rate in rates:
        session.add(CurrencyRate(
            from_currency=from_cur,
            to_currency=to_cur,
            rate=rate,
            source="manual_seed",
            observed_at=now,
        ))

    await session.commit()
    print(f"  Seeded {len(rates)} currency rates")


async def run_seeds():
    print("Seeding database...")

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    async with async_session() as session:
        await seed_products(session)
        await seed_merchants(session)
        await seed_import_rules(session)
        await seed_currency_rates(session)

    print("Done.")


if __name__ == "__main__":
    asyncio.run(run_seeds())
