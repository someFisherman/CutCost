"""Base extractor interface.

Every merchant extractor implements this contract.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExtractedOffer:
    """Raw data extracted from a merchant product page."""
    raw_title: str
    price_amount: float
    price_currency: str
    product_url: str
    ean: str | None = None
    mpn: str | None = None
    asin: str | None = None
    availability: str = "unknown"  # in_stock, out_of_stock, preorder, unknown
    condition: str = "new"
    shipping_cost: float | None = None
    shipping_currency: str | None = None
    delivery_days_min: int | None = None
    delivery_days_max: int | None = None
    image_url: str | None = None
    brand: str | None = None
    model: str | None = None
    extracted_attributes: dict = field(default_factory=dict)
    raw_data: dict = field(default_factory=dict)


class BaseExtractor(ABC):
    """Abstract base for per-merchant extractors."""

    merchant_slug: str
    merchant_name: str
    base_url: str

    @abstractmethod
    async def search_product(self, query: str) -> list[str]:
        """Search merchant site for a product. Return list of product page URLs."""
        ...

    @abstractmethod
    async def extract_offer(self, url: str) -> ExtractedOffer | None:
        """Extract offer data from a single product page URL."""
        ...

    async def extract_multiple(self, urls: list[str]) -> list[ExtractedOffer]:
        """Extract offers from multiple URLs. Override for batch optimization."""
        results = []
        for url in urls:
            offer = await self.extract_offer(url)
            if offer:
                results.append(offer)
        return results
