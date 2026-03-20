"""Digitec.ch / Galaxus.ch extractor.

Uses the public GraphQL API (productDetailsLegacy query).
The search endpoint no longer works externally — we use curated
product IDs and fetch price/offer data directly.
"""

import logging
import re
from dataclasses import dataclass

import httpx

from app.extractors.base import BaseExtractor, ExtractedOffer

logger = logging.getLogger(__name__)

PRODUCT_QUERY = """query GetProduct($id: Int!) {
  productDetailsLegacy(productId: $id) {
    product {
      id
      name
      nameProperties
    }
    offers {
      id
      offerId
      productId
      shopOfferId
      price {
        amountInclusive
        amountExclusive
        currency
      }
      deliveryOptions {
        mail {
          classification
        }
      }
      label
      type
      canAddToBasket
    }
  }
}"""

DELIVERY_MAP = {
    "TONIGHT": "same_day",
    "ONEDAY": "next_day",
    "TWODAYS": "2_days",
    "WITHIN4DAYS": "3-4_days",
    "WITHIN7DAYS": "5-7_days",
    "WITHIN17DAYS": "2-3_weeks",
}

OFFER_TYPE_TO_CONDITION = {
    "RETAIL": "new",
    "MARKETPLACE": "new",
    "RESALE": "used",
    "REFURBISHED": "refurbished",
}


def _build_headers(base_url: str, lang: str = "de") -> dict:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": base_url,
        "Referer": f"{base_url}/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "x-dg-country": "ch",
        "x-dg-language": lang,
        "x-dg-mandator": "406802",
        "x-dg-portal": "25",
        "x-dg-testgroup": "Default",
    }


def _delivery_days(classification: str) -> tuple[int | None, int | None]:
    mapping = {
        "TONIGHT": (0, 0),
        "ONEDAY": (1, 1),
        "TWODAYS": (2, 2),
        "WITHIN4DAYS": (3, 4),
        "WITHIN7DAYS": (5, 7),
        "WITHIN17DAYS": (10, 17),
    }
    return mapping.get(classification, (None, None))


class DigitecExtractor(BaseExtractor):
    merchant_slug = "digitec-ch"
    merchant_name = "digitec.ch"
    base_url = "https://www.digitec.ch"

    def __init__(self, lang: str = "de"):
        self.lang = lang
        self.graphql_url = f"{self.base_url}/api/graphql"
        self.headers = _build_headers(self.base_url, lang)

    async def search_product(self, query: str) -> list[str]:
        """Not supported externally — Digitec blocked search via API.
        Returns empty list; we use curated product IDs instead."""
        logger.info("Digitec search not available externally; use crawl jobs with known product IDs")
        return []

    async def extract_offers_by_id(self, product_id: int) -> list[ExtractedOffer]:
        """Fetch all offers for a Digitec product by numeric ID."""
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.post(
                self.graphql_url,
                json={"query": PRODUCT_QUERY, "variables": {"id": product_id}},
                headers=self.headers,
            )
            resp.raise_for_status()
            body = resp.json()

        details = (body.get("data") or {}).get("productDetailsLegacy")
        if not details:
            return []

        product = details.get("product", {})
        raw_offers = details.get("offers", [])

        name = product.get("name", "")
        name_props = product.get("nameProperties", "")
        full_name = f"{name}, {name_props}" if name_props else name

        product_url = f"{self.base_url}/{self.lang}/product/{product_id}"

        results = []
        for raw in raw_offers:
            pricing = raw.get("price", {})
            price = pricing.get("amountInclusive")
            if price is None:
                continue

            currency = pricing.get("currency", "CHF")
            offer_type = raw.get("type", "RETAIL")
            condition = OFFER_TYPE_TO_CONDITION.get(offer_type, "new")
            offer_id = str(raw.get("offerId", ""))

            offer_url = f"{product_url}?offerId={offer_id}"
            if condition == "refurbished":
                offer_url = f"{product_url}?offertype=refurbished&offerid={offer_id}"
            elif condition == "used":
                offer_url = f"{product_url}?offertype=occasion&offerid={offer_id}"

            delivery_class = (
                raw.get("deliveryOptions", {})
                .get("mail", {})
                .get("classification", "")
            )
            delivery_label = DELIVERY_MAP.get(delivery_class, delivery_class.lower())

            delivery_min, delivery_max = _delivery_days(delivery_class)

            results.append(ExtractedOffer(
                raw_title=full_name,
                price_amount=float(price),
                price_currency=currency,
                product_url=offer_url,
                ean=None,
                availability="in_stock" if raw.get("canAddToBasket") else "out_of_stock",
                condition=condition,
                shipping_cost=0.0,
                shipping_currency="CHF",
                delivery_days_min=delivery_min,
                delivery_days_max=delivery_max,
                image_url=None,
                brand="",
                extracted_attributes={
                    "offer_type": offer_type,
                    "delivery": delivery_label,
                    "offer_id": offer_id,
                    "label": raw.get("label", ""),
                },
                raw_data=raw,
            ))

        return results

    async def extract_offer(self, url: str) -> ExtractedOffer | None:
        """Extract the best (retail) offer from a Digitec product URL."""
        product_id = self._extract_product_id(url)
        if product_id is None:
            logger.warning("Could not extract product ID from URL: %s", url)
            return None

        offers = await self.extract_offers_by_id(product_id)
        if not offers:
            return None

        retail = [o for o in offers if o.condition == "new"]
        return retail[0] if retail else offers[0]

    def _extract_product_id(self, url: str) -> int | None:
        match = re.search(r"/product/(\d+)", url)
        if match:
            return int(match.group(1))
        match = re.search(r"-(\d+)(?:\?|#|$)", url)
        if match:
            return int(match.group(1))
        return None


class GalaxusExtractor(DigitecExtractor):
    """Galaxus uses the same backend API as Digitec."""
    merchant_slug = "galaxus-ch"
    merchant_name = "galaxus.ch"
    base_url = "https://www.galaxus.ch"
