"""True Total Cost Engine.

Calculates the estimated total cost of an offer delivered to the buyer's country,
including currency conversion, shipping, import duties, VAT, and customs fees.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.cost import CurrencyRate, ImportRule
from app.models.merchant import Merchant, MerchantShippingRule


@dataclass
class CostComponent:
    value: float
    currency: str
    source: str  # "extracted", "curated", "estimated", "unknown"
    note: str = ""


@dataclass
class TotalCostBreakdown:
    base_price: CostComponent
    shipping: CostComponent
    import_vat: CostComponent
    customs_fee: CostComponent
    import_duty: CostComponent
    total: float
    total_low: float | None
    total_high: float | None
    currency: str
    confidence: str  # "high", "medium", "low"
    exchange_rate: float | None
    exchange_spread: float


async def get_exchange_rate(
    db: AsyncSession, from_currency: str, to_currency: str
) -> float | None:
    if from_currency == to_currency:
        return 1.0

    result = await db.execute(
        select(CurrencyRate)
        .where(CurrencyRate.from_currency == from_currency)
        .where(CurrencyRate.to_currency == to_currency)
        .order_by(CurrencyRate.observed_at.desc())
        .limit(1)
    )
    rate = result.scalar_one_or_none()
    return float(rate.rate) if rate else None


async def get_import_rule(
    db: AsyncSession, buyer_country: str, category: str | None
) -> ImportRule | None:
    result = await db.execute(
        select(ImportRule)
        .where(ImportRule.buyer_country == buyer_country)
        .where(
            (ImportRule.product_category == category)
            | (ImportRule.product_category.is_(None))
        )
        .order_by(ImportRule.product_category.desc().nulls_last())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_shipping_rule(
    db: AsyncSession, merchant_id, buyer_country: str
) -> MerchantShippingRule | None:
    result = await db.execute(
        select(MerchantShippingRule)
        .where(MerchantShippingRule.merchant_id == merchant_id)
        .where(MerchantShippingRule.destination_country == buyer_country)
    )
    return result.scalar_one_or_none()


def _round(val: float) -> float:
    return float(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


async def calculate_total_cost(
    db: AsyncSession,
    price_amount: float,
    price_currency: str,
    merchant: Merchant,
    buyer_country: str,
    buyer_currency: str,
    category: str | None = None,
    offer_shipping_cost: float | None = None,
    offer_shipping_currency: str | None = None,
) -> TotalCostBreakdown:
    spread = settings.default_exchange_spread
    confidence = "high"

    # 1. Currency conversion
    if price_currency == buyer_currency:
        base_local = price_amount
        exchange_rate = 1.0
    else:
        rate = await get_exchange_rate(db, price_currency, buyer_currency)
        if rate is None:
            rate = await get_exchange_rate(db, buyer_currency, price_currency)
            if rate:
                rate = 1.0 / rate
        if rate is None:
            base_local = price_amount  # fallback — show original price
            exchange_rate = None
            confidence = "low"
        else:
            exchange_rate = rate
            base_local = price_amount * rate * (1 + spread)

    base_local = _round(base_local)
    base_source = "extracted" if exchange_rate == 1.0 else "estimated"
    rate_note = ""
    if exchange_rate and exchange_rate != 1.0:
        rate_note = (
            f"{price_currency} {price_amount:.2f} × {exchange_rate:.4f} + "
            f"{spread * 100:.1f}% spread"
        )

    # 2. Shipping
    shipping_cost = 0.0
    shipping_source = "unknown"
    shipping_note = ""

    if offer_shipping_cost is not None:
        sc = offer_shipping_cost
        if offer_shipping_currency and offer_shipping_currency != buyer_currency and exchange_rate:
            sc_rate = await get_exchange_rate(db, offer_shipping_currency, buyer_currency)
            sc = offer_shipping_cost * (sc_rate or exchange_rate or 1.0)
        shipping_cost = _round(sc)
        shipping_source = "extracted"
    else:
        rule = await get_shipping_rule(db, merchant.id, buyer_country)
        if rule:
            if rule.free_above and base_local >= float(rule.free_above):
                shipping_cost = 0.0
                shipping_note = "Free shipping"
            elif rule.cost_amount is not None:
                sc = float(rule.cost_amount)
                if rule.cost_currency != buyer_currency:
                    sc_rate = await get_exchange_rate(db, rule.cost_currency, buyer_currency)
                    sc = sc * (sc_rate or 1.0)
                shipping_cost = _round(sc)
            shipping_source = "curated"
        else:
            confidence = "low" if confidence == "medium" else ("medium" if confidence == "high" else confidence)

    # 3. Import costs
    import_vat = 0.0
    customs_fee_val = 0.0
    duty = 0.0
    import_source = "estimated"
    import_note = ""

    if merchant.country == buyer_country:
        import_source = "curated"
        import_note = "Domestic purchase"
    else:
        rule = await get_import_rule(db, buyer_country, category)
        if rule:
            taxable = base_local + shipping_cost
            vat_amount = _round(taxable * float(rule.vat_rate))
            if rule.de_minimis_amount and vat_amount < float(rule.de_minimis_amount):
                import_note = f"VAT ({vat_amount:.2f}) below de minimis threshold"
            else:
                import_vat = vat_amount
                customs_fee_val = _round(float(rule.customs_fee))
                import_note = f"{float(rule.vat_rate) * 100:.1f}% VAT on goods + shipping"
            duty = _round(taxable * float(rule.duty_rate))
        else:
            confidence = "low"

    total = _round(base_local + shipping_cost + import_vat + customs_fee_val + duty)

    # Confidence intervals: ±5% for medium, ±10% for low
    total_low = None
    total_high = None
    if confidence == "medium":
        total_low = _round(total * 0.95)
        total_high = _round(total * 1.05)
    elif confidence == "low":
        total_low = _round(total * 0.90)
        total_high = _round(total * 1.10)

    return TotalCostBreakdown(
        base_price=CostComponent(base_local, buyer_currency, base_source, rate_note),
        shipping=CostComponent(shipping_cost, buyer_currency, shipping_source, shipping_note),
        import_vat=CostComponent(import_vat, buyer_currency, import_source, import_note),
        customs_fee=CostComponent(customs_fee_val, buyer_currency, import_source, ""),
        import_duty=CostComponent(duty, buyer_currency, import_source, ""),
        total=total,
        total_low=total_low,
        total_high=total_high,
        currency=buyer_currency,
        confidence=confidence,
        exchange_rate=exchange_rate,
        exchange_spread=spread,
    )
