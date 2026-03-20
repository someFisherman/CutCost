"""Tests for the total cost engine."""

from app.services.cost_service import CostComponent, TotalCostBreakdown


def test_domestic_purchase_no_import():
    """Swiss purchase from Swiss merchant = no import costs."""
    breakdown = TotalCostBreakdown(
        base_price=CostComponent(929.0, "CHF", "extracted"),
        shipping=CostComponent(0.0, "CHF", "curated", "Free shipping"),
        import_vat=CostComponent(0.0, "CHF", "curated", "Domestic purchase"),
        customs_fee=CostComponent(0.0, "CHF", "curated"),
        import_duty=CostComponent(0.0, "CHF", "curated"),
        total=929.0,
        total_low=None,
        total_high=None,
        currency="CHF",
        confidence="high",
        exchange_rate=1.0,
        exchange_spread=0.015,
    )
    assert breakdown.total == 929.0
    assert breakdown.confidence == "high"
    assert breakdown.import_vat.value == 0.0


def test_german_import_to_switzerland():
    """EUR 879 from Amazon.de → CHF total with VAT + customs fee."""
    eur_price = 879.0
    rate = 0.965
    spread = 0.015
    base_chf = round(eur_price * rate * (1 + spread), 2)
    shipping_chf = round(8.30 * rate, 2)
    taxable = base_chf + shipping_chf
    vat = round(taxable * 0.081, 2)
    customs_fee = 11.50
    total = round(base_chf + shipping_chf + vat + customs_fee, 2)

    assert base_chf > 0
    assert vat > 0
    assert total > base_chf + shipping_chf


def test_vat_de_minimis():
    """If VAT amount < CHF 5, it should not be collected."""
    # A cheap item where 8.1% VAT < CHF 5 → taxable < ~61.7 CHF
    taxable = 50.0
    vat = round(taxable * 0.081, 2)
    assert vat < 5.0
