"""Search & Query Understanding Service.

Handles query normalization, autocomplete, product lookup, disambiguation,
and intelligent query-to-filter parsing (e.g. "iphon 256gb 16 blak" -> filters).
"""

import re
import unicodedata
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product, ProductSearchAlias, ProductVariant


BRAND_ALIASES: dict[str, str] = {
    "apple": "Apple", "iphone": "Apple", "iphon": "Apple", "ipone": "Apple",
    "samsung": "Samsung", "samung": "Samsung", "samsng": "Samsung",
    "google": "Google", "pixel": "Google", "pixl": "Google",
    "huawei": "Huawei", "xiaomi": "Xiaomi",
    "oneplus": "OnePlus", "sony": "Sony",
}

PRODUCT_LINE_ALIASES: dict[str, str] = {
    "iphone": "iPhone", "iphon": "iPhone", "ipone": "iPhone",
    "galaxy": "Galaxy", "galxy": "Galaxy",
    "pixel": "Pixel", "pixl": "Pixel",
}

STORAGE_PATTERN = re.compile(r"(\d+)\s*(gb|tb)", re.IGNORECASE)

COLOR_ALIASES: dict[str, str] = {
    "black": "Black", "blak": "Black", "blck": "Black", "schwarz": "Black",
    "white": "White", "whit": "White", "weiss": "White", "weis": "White",
    "blue": "Blue", "blau": "Blue", "blu": "Blue",
    "titanium": "Titanium", "titan": "Titanium",
    "desert": "Desert", "natural": "Natural", "obsidian": "Obsidian",
    "porcelain": "Porcelain", "gray": "Gray", "grey": "Gray", "grau": "Gray",
    "gold": "Gold", "silver": "Silver", "silber": "Silver",
    "red": "Red", "rot": "Red", "green": "Green", "grün": "Green", "gruen": "Green",
    "pink": "Pink", "rosa": "Pink", "purple": "Purple", "lila": "Purple",
}

MODEL_PATTERN = re.compile(
    r"(?:^|\s)((?:s?\d{1,2})\s*(?:pro\s*max|pro|ultra|plus|\+|lite|mini|fe)?)",
    re.IGNORECASE,
)


@dataclass
class ParsedQuery:
    brand: str | None = None
    product_line: str | None = None
    model: str | None = None
    storage: str | None = None
    color: str | None = None
    remainder: str = ""
    original: str = ""
    has_filters: bool = False


def normalize_query(raw: str) -> str:
    """Lowercase, strip accents, collapse whitespace, remove special chars."""
    text = raw.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s\-.]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_query_to_filters(raw: str) -> ParsedQuery:
    """Deterministically extract brand/model/storage/color from free text."""
    normalized = normalize_query(raw)
    tokens = normalized.split()
    parsed = ParsedQuery(original=raw)
    remaining: list[str] = []

    for token in tokens:
        if token in BRAND_ALIASES and not parsed.brand:
            parsed.brand = BRAND_ALIASES[token]
            if token in PRODUCT_LINE_ALIASES and not parsed.product_line:
                parsed.product_line = PRODUCT_LINE_ALIASES[token]
            continue
        if token in PRODUCT_LINE_ALIASES and not parsed.product_line:
            parsed.product_line = PRODUCT_LINE_ALIASES[token]
            if token in BRAND_ALIASES and not parsed.brand:
                parsed.brand = BRAND_ALIASES[token]
            continue
        if token in COLOR_ALIASES and not parsed.color:
            parsed.color = COLOR_ALIASES[token]
            continue
        remaining.append(token)

    remaining_text = " ".join(remaining)

    storage_match = STORAGE_PATTERN.search(remaining_text)
    if storage_match:
        num = int(storage_match.group(1))
        unit = storage_match.group(2).upper()
        parsed.storage = f"{num}{unit}"
        remaining_text = remaining_text[:storage_match.start()] + remaining_text[storage_match.end():]

    model_match = MODEL_PATTERN.search(remaining_text)
    if model_match:
        raw_model = model_match.group(1).strip()
        parsed.model = _normalize_model(raw_model)
        remaining_text = remaining_text[:model_match.start()] + remaining_text[model_match.end():]

    parsed.remainder = remaining_text.strip()
    parsed.has_filters = any([parsed.brand, parsed.product_line, parsed.model, parsed.storage, parsed.color])
    return parsed


def _normalize_model(raw: str) -> str:
    """Clean up model string: '16promax' -> '16 Pro Max'."""
    raw = raw.strip()
    raw = re.sub(r"promax", "Pro Max", raw, flags=re.IGNORECASE)
    raw = re.sub(r"pro\s*max", "Pro Max", raw, flags=re.IGNORECASE)
    raw = re.sub(r"(?<!\w)pro(?!\w)", "Pro", raw, flags=re.IGNORECASE)
    raw = re.sub(r"(?<!\w)ultra(?!\w)", "Ultra", raw, flags=re.IGNORECASE)
    raw = re.sub(r"(?<!\w)plus(?!\w)", "Plus", raw, flags=re.IGNORECASE)
    raw = re.sub(r"(?<!\w)mini(?!\w)", "Mini", raw, flags=re.IGNORECASE)
    raw = re.sub(r"(?<!\w)lite(?!\w)", "Lite", raw, flags=re.IGNORECASE)
    raw = re.sub(r"(?<!\w)fe(?!\w)", "FE", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\+", " Plus", raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


async def autocomplete(
    db: AsyncSession, partial: str, limit: int = 8
) -> list[dict]:
    """Return product suggestions matching partial input, including category suggestions."""
    if len(partial) < 2:
        return []

    normalized = normalize_query(partial)
    parsed = parse_query_to_filters(partial)
    suggestions: list[dict] = []

    if parsed.has_filters and not parsed.storage and not parsed.color:
        category_results = await db.execute(
            select(Product.brand, Product.product_line, func.count(ProductVariant.id))
            .join(ProductVariant)
            .where(
                or_(
                    func.lower(Product.brand) == (parsed.brand or "").lower(),
                    func.lower(Product.product_line) == (parsed.product_line or "").lower(),
                    Product.canonical_name.ilike(f"%{normalized}%"),
                )
            )
            .group_by(Product.brand, Product.product_line)
            .limit(3)
        )
        for brand, pline, count in category_results.all():
            label = f"{brand} {pline}" if pline else brand
            suggestions.append({
                "variant_id": "",
                "product_id": "",
                "display_name": f"Browse all {label} ({count} variants)",
                "slug": "",
                "category": "smartphone",
                "brand": brand,
                "image_url": None,
                "type": "category",
                "filter_url": f"/browse?brand={brand}" + (f"&product_line={pline}" if pline else ""),
            })

    results = await db.execute(
        select(ProductVariant)
        .join(Product)
        .where(
            or_(
                func.similarity(ProductVariant.display_name, normalized) > 0.1,
                ProductVariant.display_name.ilike(f"%{normalized}%"),
            )
        )
        .order_by(func.similarity(ProductVariant.display_name, normalized).desc())
        .limit(limit - len(suggestions))
        .options(selectinload(ProductVariant.product))
    )
    variants = results.scalars().all()

    for v in variants:
        suggestions.append({
            "variant_id": str(v.id),
            "product_id": str(v.product_id),
            "display_name": v.display_name,
            "slug": v.slug,
            "category": v.product.category,
            "brand": v.product.brand,
            "image_url": v.image_url or v.product.image_url,
            "type": "variant",
            "filter_url": None,
        })

    return suggestions


async def search_products(
    db: AsyncSession, query: str
) -> dict:
    """
    Search for products matching a query.

    Returns:
        - exact_variant: if query matches one variant clearly
        - variants: if query matches multiple variants of same product (disambiguation)
        - products: if query matches multiple products
        - parsed_filters: detected filters from the query
        - empty: if no match
    """
    normalized = normalize_query(query)
    parsed = parse_query_to_filters(query)

    # 1. Try exact slug match
    variant = await db.execute(
        select(ProductVariant)
        .where(ProductVariant.slug == _slugify(normalized))
        .options(selectinload(ProductVariant.product))
    )
    exact = variant.scalar_one_or_none()
    if exact:
        return {
            "type": "exact", "variant": exact, "variants": [], "products": [],
            "parsed": parsed,
        }

    # 2. Try alias match
    alias_result = await db.execute(
        select(ProductSearchAlias)
        .where(ProductSearchAlias.alias == normalized)
    )
    alias = alias_result.scalar_one_or_none()
    if alias and alias.variant_id:
        v = await db.get(ProductVariant, alias.variant_id, options=[selectinload(ProductVariant.product)])
        if v:
            return {
                "type": "exact", "variant": v, "variants": [], "products": [],
                "parsed": parsed,
            }

    # 3. Full-text + trigram search on variants
    results = await db.execute(
        select(ProductVariant)
        .join(Product)
        .where(
            or_(
                ProductVariant.display_name.ilike(f"%{normalized}%"),
                func.similarity(ProductVariant.display_name, normalized) > 0.15,
            )
        )
        .order_by(func.similarity(ProductVariant.display_name, normalized).desc())
        .limit(20)
        .options(selectinload(ProductVariant.product))
    )
    matches = results.scalars().all()

    if not matches:
        if parsed.has_filters:
            return {
                "type": "browse_redirect", "variant": None, "variants": [], "products": [],
                "parsed": parsed,
            }
        return {
            "type": "empty", "variant": None, "variants": [], "products": [],
            "parsed": parsed,
        }

    if len(matches) == 1:
        return {
            "type": "exact", "variant": matches[0], "variants": [], "products": [],
            "parsed": parsed,
        }

    product_ids = {m.product_id for m in matches}
    if len(product_ids) == 1:
        return {
            "type": "disambiguation", "variant": None, "variants": matches, "products": [],
            "parsed": parsed,
        }

    return {
        "type": "multiple", "variant": None, "variants": matches[:10], "products": [],
        "parsed": parsed,
    }


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")
