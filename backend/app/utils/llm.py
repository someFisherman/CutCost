"""LLM client with caching for structured extraction."""

import hashlib
import json
import logging

from anthropic import AsyncAnthropic

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None
_cache: dict[str, str] = {}  # in-memory cache; replace with Redis in production


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


TITLE_EXTRACTION_PROMPT = """Extract product attributes from this merchant listing title.

Title: "{title}"
Merchant: {merchant}
Category: {category}

Respond with JSON only, matching this exact schema:
{{
  "brand": "string or null",
  "product_line": "string or null",
  "model": "string or null",
  "storage": "string or null",
  "color": "string or null",
  "condition": "new|refurbished|used|open_box|unknown",
  "bundle_items": [],
  "confidence": "high|medium|low"
}}

Rules:
- Extract only what is explicitly stated in the title
- Do not guess or infer missing attributes
- "model" should be the specific model identifier (e.g., "15 Pro", "S24 Ultra", "A7 IV")
- "product_line" should be the product line name (e.g., "iPhone", "Galaxy", "Alpha")
- Set confidence to "low" if the title is ambiguous or incomplete
"""


async def extract_title_attributes(
    title: str, merchant: str, category: str = "electronics"
) -> dict | None:
    """Extract product attributes from a merchant listing title using Claude."""
    if not settings.anthropic_api_key:
        return None

    prompt = TITLE_EXTRACTION_PROMPT.format(
        title=title, merchant=merchant, category=category
    )

    key = _cache_key(prompt)
    if key in _cache:
        return json.loads(_cache[key])

    try:
        client = _get_client()
        response = await client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(text)
        _cache[key] = json.dumps(result)
        return result

    except Exception:
        logger.exception("LLM extraction failed for title: %s", title[:100])
        return None
