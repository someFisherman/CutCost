"""Amazon.de extractor.

Uses direct product page scraping with httpx + BeautifulSoup.
Amazon frequently changes their HTML, so this may need updates.
Requires careful rate limiting to avoid blocking.
"""

import logging
import re
from dataclasses import dataclass

import httpx
from selectolax.parser import HTMLParser

from app.extractors.base import BaseExtractor, ExtractedOffer

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}


class AmazonDeExtractor(BaseExtractor):
    merchant_slug = "amazon-de"
    merchant_name = "Amazon.de"
    base_url = "https://www.amazon.de"

    async def search_product(self, query: str) -> list[str]:
        logger.info("Amazon search not implemented — use ASIN-based lookups")
        return []

    async def extract_offer(self, url: str) -> ExtractedOffer | None:
        """Extract offer from an Amazon.de product page URL."""
        try:
            async with httpx.AsyncClient(
                timeout=20, follow_redirects=True, headers=HEADERS
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
        except Exception as e:
            logger.error("Failed to fetch Amazon URL %s: %s", url, e)
            return None

        return self._parse_product_page(html, url)

    async def extract_offer_by_asin(self, asin: str) -> ExtractedOffer | None:
        """Extract offer by ASIN."""
        url = f"{self.base_url}/dp/{asin}"
        return await self.extract_offer(url)

    def _parse_product_page(self, html: str, url: str) -> ExtractedOffer | None:
        tree = HTMLParser(html)

        title_el = tree.css_first("#productTitle")
        title = title_el.text(strip=True) if title_el else ""
        if not title:
            logger.warning("Could not find product title on %s", url)
            return None

        price = self._extract_price(tree)
        if price is None:
            logger.warning("Could not find price on %s", url)
            return None

        availability = "in_stock"
        avail_el = tree.css_first("#availability span")
        if avail_el:
            avail_text = avail_el.text(strip=True).lower()
            if "nicht verfügbar" in avail_text or "not available" in avail_text:
                availability = "out_of_stock"
            elif "vorbestellung" in avail_text or "pre-order" in avail_text:
                availability = "preorder"

        brand = ""
        brand_el = tree.css_first("#bylineInfo")
        if brand_el:
            brand = brand_el.text(strip=True).replace("Besuche den ", "").replace("-Store", "").strip()

        image_url = None
        img_el = tree.css_first("#landingImage")
        if img_el:
            image_url = img_el.attributes.get("src")

        return ExtractedOffer(
            raw_title=title,
            price_amount=price,
            price_currency="EUR",
            product_url=url,
            asin=self._extract_asin(url),
            availability=availability,
            condition="new",
            shipping_cost=None,
            shipping_currency="EUR",
            image_url=image_url,
            brand=brand,
            extracted_attributes={},
        )

    def _extract_price(self, tree: HTMLParser) -> float | None:
        for selector in [
            ".a-price .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            ".apexPriceToPay .a-offscreen",
            "#corePrice_feature_div .a-offscreen",
        ]:
            el = tree.css_first(selector)
            if el:
                text = el.text(strip=True)
                return self._parse_price_text(text)
        return None

    def _parse_price_text(self, text: str) -> float | None:
        text = text.replace("\xa0", " ").replace("€", "").replace("EUR", "").strip()
        text = text.replace(".", "").replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return None

    def _extract_asin(self, url: str) -> str | None:
        match = re.search(r"/dp/([A-Z0-9]{10})", url)
        return match.group(1) if match else None
