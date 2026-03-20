"""Affiliate URL helpers."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.config import settings

AMAZON_AFFILIATE_TAG = "audix-20"


def build_affiliate_url(url: str, merchant_slug: str) -> str | None:
    """Return affiliate URL when possible; otherwise None."""
    if not url:
        return None

    if merchant_slug.startswith("amazon-") and "amazon." in url:
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        # Force the requested associate tag for all Amazon links.
        query["tag"] = AMAZON_AFFILIATE_TAG
        new_query = urlencode(query, doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

    return None
