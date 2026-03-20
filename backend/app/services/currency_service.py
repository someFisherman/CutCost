"""Currency Rate Service.

Fetches and stores exchange rates from public APIs.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cost import CurrencyRate

logger = logging.getLogger(__name__)

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

TARGET_PAIRS = [
    ("EUR", "CHF"),
    ("USD", "CHF"),
    ("GBP", "CHF"),
    ("EUR", "USD"),
    ("EUR", "GBP"),
]


async def fetch_ecb_rates() -> dict[str, float]:
    """Fetch daily reference rates from ECB (base: EUR)."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(ECB_URL)
        resp.raise_for_status()

    rates: dict[str, float] = {"EUR": 1.0}
    import xml.etree.ElementTree as ET

    root = ET.fromstring(resp.text)
    ns = {"gesmes": "http://www.gesmes.org/xml/2002-08-01",
          "eurofxref": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}

    for cube in root.findall(".//eurofxref:Cube[@currency]", ns):
        currency = cube.get("currency", "")
        rate_str = cube.get("rate", "")
        if currency and rate_str:
            rates[currency] = float(rate_str)

    return rates


def compute_cross_rate(
    base_rates: dict[str, float], from_currency: str, to_currency: str
) -> float | None:
    """Compute cross rate from EUR-based rates."""
    if from_currency not in base_rates or to_currency not in base_rates:
        return None
    return base_rates[to_currency] / base_rates[from_currency]


async def update_currency_rates(db: AsyncSession) -> int:
    """Fetch ECB rates and store all target pairs. Returns count of rates stored."""
    try:
        eur_rates = await fetch_ecb_rates()
    except Exception:
        logger.exception("Failed to fetch ECB rates")
        return 0

    now = datetime.now(timezone.utc)
    count = 0

    for from_cur, to_cur in TARGET_PAIRS:
        rate = compute_cross_rate(eur_rates, from_cur, to_cur)
        if rate is None:
            continue

        db.add(CurrencyRate(
            from_currency=from_cur,
            to_currency=to_cur,
            rate=rate,
            source="ecb",
            observed_at=now,
        ))
        count += 1

    await db.commit()
    logger.info("Stored %d currency rates", count)
    return count
