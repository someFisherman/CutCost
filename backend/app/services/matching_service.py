"""Product Matching Service.

Matches extracted offers to canonical products using identifiers and attributes.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import ProductIdentifier, ProductVariant


@dataclass
class MatchResult:
    variant_id: str | None
    confidence: float
    method: str
    reasons: list[str] = field(default_factory=list)
    mismatch_flags: list[dict] = field(default_factory=list)


async def match_by_identifier(
    db: AsyncSession,
    identifier_type: str,
    identifier_value: str,
) -> MatchResult | None:
    """Try to match by exact identifier (EAN, MPN, ASIN)."""
    result = await db.execute(
        select(ProductIdentifier)
        .where(ProductIdentifier.identifier_type == identifier_type)
        .where(ProductIdentifier.value == identifier_value)
        .options(selectinload(ProductIdentifier.variant))
    )
    pi = result.scalar_one_or_none()
    if pi is None:
        return None

    confidence_map = {"ean": 0.99, "gtin": 0.99, "upc": 0.99, "mpn": 0.95, "asin": 0.90}
    conf = confidence_map.get(identifier_type, 0.85)

    return MatchResult(
        variant_id=str(pi.variant_id),
        confidence=conf,
        method=f"{identifier_type}_exact",
        reasons=[f"{identifier_type.upper()} {identifier_value} matches canonical product"],
    )


def compute_attribute_similarity(
    extracted: dict, canonical_attrs: dict, brand: str | None, model: str | None,
    canonical_brand: str, canonical_model: str
) -> MatchResult:
    """Score match based on extracted attributes vs canonical product attributes."""
    score = 0.0
    reasons: list[str] = []
    mismatches: list[dict] = []

    # Brand match
    if brand:
        if brand.lower() == canonical_brand.lower():
            score += 0.15
            reasons.append(f"Brand match: {brand}")
        else:
            return MatchResult(None, 0.0, "attribute_full", ["Brand mismatch"],
                               [{"code": "brand_mismatch", "detail": f"{brand} vs {canonical_brand}"}])

    # Model match
    if model:
        ext_model = model.lower().strip()
        can_model = canonical_model.lower().strip()
        if ext_model == can_model:
            score += 0.15
            reasons.append(f"Model match: {model}")
        elif ext_model in can_model or can_model in ext_model:
            score += 0.08
            reasons.append(f"Partial model match: {model}")
            mismatches.append({"code": "model_partial", "detail": f"'{model}' vs '{canonical_model}'"})
        else:
            score += 0.0
            mismatches.append({"code": "model_variant", "detail": f"'{model}' vs '{canonical_model}'"})
            return MatchResult(None, score, "attribute_partial", reasons, mismatches)

    # Storage
    ext_storage = _normalize_storage(extracted.get("storage", ""))
    can_storage = _normalize_storage(canonical_attrs.get("storage", ""))
    if ext_storage and can_storage:
        if ext_storage == can_storage:
            score += 0.10
            reasons.append(f"Storage match: {can_storage}")
        else:
            score -= 0.40
            mismatches.append({
                "code": "storage_mismatch",
                "detail": f"{ext_storage} vs {can_storage}"
            })

    # Color
    ext_color = _normalize_color(extracted.get("color", ""))
    can_color = _normalize_color(canonical_attrs.get("color", ""))
    if ext_color and can_color:
        if ext_color == can_color:
            score += 0.05
            reasons.append(f"Color match: {canonical_attrs.get('color')}")
        else:
            mismatches.append({
                "code": "color_mismatch",
                "detail": f"{extracted.get('color')} vs {canonical_attrs.get('color')}"
            })

    method = "attribute_full" if score >= 0.30 else "attribute_partial"
    return MatchResult(
        variant_id=None,
        confidence=max(0.0, min(1.0, score)),
        method=method,
        reasons=reasons,
        mismatch_flags=mismatches,
    )


async def match_offer(
    db: AsyncSession,
    identifiers: list[dict],
    extracted_attrs: dict,
    brand: str | None = None,
    model: str | None = None,
) -> MatchResult:
    """Main matching pipeline: identifier match → attribute match."""
    # Step 1: Try identifier-based matching
    for ident in identifiers:
        result = await match_by_identifier(db, ident["type"], ident["value"])
        if result:
            return result

    # Step 2: Attribute-based matching against all variants
    if not brand and not model:
        return MatchResult(None, 0.0, "none", ["No identifiers or attributes to match"])

    all_variants = await db.execute(
        select(ProductVariant).options(selectinload(ProductVariant.product))
    )
    variants = all_variants.scalars().all()

    best_match: MatchResult | None = None
    for variant in variants:
        product = variant.product
        result = compute_attribute_similarity(
            extracted_attrs, variant.attributes,
            brand, model,
            product.brand, product.model,
        )
        if result.confidence > 0 and (best_match is None or result.confidence > best_match.confidence):
            result.variant_id = str(variant.id)
            best_match = result

    if best_match:
        return best_match

    return MatchResult(None, 0.0, "none", ["No matching product found"])


def _normalize_storage(s: str) -> str:
    """Normalize storage strings: '256 GB' → '256gb', '0.5TB' → '512gb'."""
    if not s:
        return ""
    s = s.lower().strip().replace(" ", "")
    if s.endswith("tb"):
        try:
            val = float(s[:-2]) * 1024
            return f"{int(val)}gb"
        except ValueError:
            pass
    return s


def _normalize_color(c: str) -> str:
    """Normalize color strings to lowercase slug form."""
    if not c:
        return ""
    return c.lower().strip().replace(" ", "-").replace(".", "")
