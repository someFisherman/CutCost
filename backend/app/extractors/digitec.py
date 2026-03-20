"""Digitec.ch / Galaxus.ch extractor.

Uses the public GraphQL API at digitec.ch/api/graphql.
Same API works for galaxus.ch with minor URL differences.
"""

import logging
import re

import httpx

from app.extractors.base import BaseExtractor, ExtractedOffer

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://www.digitec.ch/api/graphql"

SEARCH_QUERY = """
query SEARCH_PRODUCTS($query: String!) {
  search(query: $query) {
    products {
      hasMore
      results {
        ... on Product {
          productId
          name
          brandName
          nameProperties
          productTypeName
          pricing {
            price {
              amountIncl
              currency
            }
          }
          availability {
            label
          }
          url
          images {
            url
          }
        }
      }
    }
  }
}
"""

PRODUCT_DETAIL_QUERY = """
query PRODUCT_DETAIL($productId: Int!) {
  productDetails(productId: $productId) {
    product {
      productId
      name
      brandName
      nameProperties
      productTypeName
      pricing {
        price {
          amountIncl
          currency
        }
      }
      availability {
        label
        deliveryDate
      }
      url
      images {
        url
      }
      specifications {
        name
        propertyGroups {
          name
          properties {
            name
            value
          }
        }
      }
    }
  }
}
"""

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "CutCost/0.1 (price-comparison; contact@cutcost.com)",
}


class DigitecExtractor(BaseExtractor):
    merchant_slug = "digitec-ch"
    merchant_name = "digitec.ch"
    base_url = "https://www.digitec.ch"

    def __init__(self, lang: str = "de"):
        self.lang = lang
        self.headers = {**HEADERS, "x-dg-language": lang}

    async def search_product(self, query: str) -> list[str]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                GRAPHQL_URL,
                json={"query": SEARCH_QUERY, "variables": {"query": query}},
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()

        results = (
            data.get("data", {})
            .get("search", {})
            .get("products", {})
            .get("results", [])
        )

        urls = []
        for r in results[:10]:
            url = r.get("url")
            if url:
                if not url.startswith("http"):
                    url = f"{self.base_url}{url}"
                urls.append(url)

        return urls

    async def extract_offer(self, url: str) -> ExtractedOffer | None:
        product_id = self._extract_product_id(url)
        if product_id is None:
            logger.warning("Could not extract product ID from URL: %s", url)
            return None

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                GRAPHQL_URL,
                json={
                    "query": PRODUCT_DETAIL_QUERY,
                    "variables": {"productId": product_id},
                },
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()

        product = (
            data.get("data", {})
            .get("productDetails", {})
            .get("product")
        )
        if not product:
            return None

        pricing = product.get("pricing", {}).get("price", {})
        price = pricing.get("amountIncl")
        currency = pricing.get("currency", "CHF")

        if price is None:
            return None

        availability_label = (
            product.get("availability", {}).get("label", "")
        )
        availability = "in_stock" if availability_label else "unknown"
        if availability_label and any(
            kw in availability_label.lower()
            for kw in ["nicht", "out of", "unavailable", "ausverkauft"]
        ):
            availability = "out_of_stock"

        name_props = product.get("nameProperties", "")
        brand = product.get("brandName", "")
        full_name = f"{brand} {product.get('name', '')}".strip()
        if name_props:
            full_name = f"{full_name}, {name_props}"

        images = product.get("images", [])
        image_url = images[0].get("url") if images else None

        attrs = self._extract_specs(product.get("specifications", []))
        ean = attrs.pop("ean", None) or attrs.pop("gtin", None)

        return ExtractedOffer(
            raw_title=full_name,
            price_amount=float(price),
            price_currency=currency,
            product_url=url,
            ean=ean,
            availability=availability,
            condition="new",
            shipping_cost=0.0,
            shipping_currency="CHF",
            image_url=image_url,
            brand=brand,
            extracted_attributes=attrs,
            raw_data=product,
        )

    def _extract_product_id(self, url: str) -> int | None:
        match = re.search(r"-(\d+)(?:\?|#|$)", url)
        if match:
            return int(match.group(1))
        match = re.search(r"/product/.*?(\d+)", url)
        if match:
            return int(match.group(1))
        return None

    def _extract_specs(self, specifications: list) -> dict:
        attrs: dict[str, str] = {}
        for spec_group in specifications:
            for prop_group in spec_group.get("propertyGroups", []):
                for prop in prop_group.get("properties", []):
                    name = prop.get("name", "").lower().strip()
                    value = prop.get("value", "").strip()
                    if not name or not value:
                        continue
                    if "ean" in name or "gtin" in name:
                        attrs["ean"] = value
                    elif "speicher" in name or "storage" in name or "kapazität" in name:
                        attrs["storage"] = value
                    elif "farbe" in name or "color" in name or "colour" in name:
                        attrs["color"] = value
                    elif "modell" in name or "model" in name:
                        attrs["model"] = value
        return attrs


class GalaxusExtractor(DigitecExtractor):
    """Galaxus uses the same API as Digitec."""
    merchant_slug = "galaxus-ch"
    merchant_name = "galaxus.ch"
    base_url = "https://www.galaxus.ch"
