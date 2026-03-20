"""Control which merchants' offers appear in browse and product APIs.

Curated links can break when a shop changes URL patterns (e.g. MediaMarkt.ch
product pages often return generic error pages). Hide those until we have a
working extractor or verified deep links.
"""

from typing import Final

EXCLUDED_OFFER_MERCHANT_SLUGS: Final[frozenset[str]] = frozenset(
    {
        "mediamarkt-ch",
    }
)

# Exact broken/dead links observed in production.
EXCLUDED_OFFER_URL_SUBSTRINGS: Final[tuple[str, ...]] = (
    "amazon.de/dp/B0CMZ4D4XF",
)
