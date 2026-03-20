"""Live test — Digitec extractor with real product IDs."""

import asyncio
import json
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx

GRAPHQL_URL = "https://www.digitec.ch/api/graphql"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://www.digitec.ch",
    "Referer": "https://www.digitec.ch/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "x-dg-country": "ch",
    "x-dg-language": "de",
    "x-dg-mandator": "406802",
    "x-dg-portal": "25",
    "x-dg-testgroup": "Default",
}

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

PRODUCTS = {
    "iPhone 16 Pro 256GB Natural Titanium": 49221237,
    "iPhone 15 Pro 256GB Black Titanium": 38606712,
    "Samsung Galaxy S24 Ultra 256GB Titanium Black": 41969659,
}


async def main():
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for name, pid in PRODUCTS.items():
            print(f"\n{'=' * 60}")
            print(f"  {name} (ID: {pid})")
            print(f"{'=' * 60}")

            resp = await client.post(
                GRAPHQL_URL,
                json={"query": PRODUCT_QUERY, "variables": {"id": pid}},
                headers=HEADERS,
            )

            if resp.status_code != 200:
                print(f"  ERROR: {resp.status_code} — {resp.text[:200]}")
                continue

            data = resp.json().get("data", {}).get("productDetailsLegacy")
            if not data:
                print("  No data returned")
                continue

            product = data.get("product", {})
            offers = data.get("offers", [])

            print(f"  Product:  {product.get('name')}")
            print(f"  Props:    {product.get('nameProperties')}")
            print(f"  Offers:   {len(offers)}")

            for i, offer in enumerate(offers[:3]):
                price = offer.get("price", {})
                delivery = offer.get("deliveryOptions", {}).get("mail", {})
                print(f"\n  Offer [{i}]:")
                print(f"    Price:     {price.get('amountInclusive')} {price.get('currency')}")
                print(f"    Type:      {offer.get('type')}")
                print(f"    Delivery:  {delivery.get('classification')}")
                print(f"    In stock:  {offer.get('canAddToBasket')}")
                print(f"    OfferID:   {offer.get('offerId')}")

    print("\n\nDone! The API works for product details.")


if __name__ == "__main__":
    asyncio.run(main())
