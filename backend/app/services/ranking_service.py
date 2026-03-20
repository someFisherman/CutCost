"""Ranking & Recommendation Engine.

Ranks offers by a composite score balancing cost, trust, delivery, and condition.
Produces labels and human-readable explanations.
"""

from dataclasses import dataclass

from app.services.cost_service import TotalCostBreakdown


@dataclass
class RankedOffer:
    offer_id: str
    rank: int
    score: float
    label: str | None  # "best_deal", "cheapest", "fastest", "risky"
    explanation: str
    total_cost: TotalCostBreakdown


EXPLANATION_TEMPLATES = {
    "cheapest_trusted_domestic": (
        "Cheapest total cost from a verified {country} merchant with "
        "{shipping_note}."
    ),
    "cheapest_trusted_import": (
        "Lowest total cost after import costs from {merchant}. "
        "{import_note}"
    ),
    "trusted_premium": (
        "{delta} more than cheapest, but from a highly trusted merchant "
        "with {delivery_note}."
    ),
    "refurbished_savings": (
        "Save {savings} vs buying new — {condition_note}."
    ),
    "suspicious_cheap": (
        "Unusually low price. {risk_count} risk signal(s) detected. "
        "Exercise caution."
    ),
    "fastest": (
        "Arrives in {days} day(s) — {days_faster} day(s) faster than the cheapest option."
    ),
    "default": (
        "{merchant} — {total_cost} total estimated cost."
    ),
}


@dataclass
class OfferForRanking:
    offer_id: str
    total_cost: float
    trust_score: float
    trust_tier: str
    delivery_days: int | None
    condition: str
    match_confidence: float
    merchant_name: str
    merchant_country: str
    is_domestic: bool
    red_flags: list[dict]
    cost_breakdown: TotalCostBreakdown


def compute_best_deal_score(offer: OfferForRanking, min_cost: float, max_cost: float) -> float:
    """Weighted composite score. Higher = better."""
    cost_range = max_cost - min_cost if max_cost > min_cost else 1.0
    cost_score = 1.0 - ((offer.total_cost - min_cost) / cost_range)

    trust_score = offer.trust_score

    delivery = offer.delivery_days or 7
    delivery_score = 1.0 - (min(delivery, 14) - 1) / 13

    condition_factors = {
        "new": 1.0, "open_box": 0.95, "refurbished": 0.85, "used": 0.70, "unknown": 0.80
    }
    condition_score = condition_factors.get(offer.condition, 0.80)

    confidence_score = offer.match_confidence or 0.5

    score = (
        0.45 * cost_score
        + 0.30 * trust_score
        + 0.10 * delivery_score
        + 0.10 * condition_score
        + 0.05 * confidence_score
    )

    if offer.trust_score < 0.30:
        score *= 0.5
    if _is_price_outlier(offer.total_cost, min_cost) and offer.trust_score < 0.60:
        score *= 0.3

    return round(score, 4)


def _is_price_outlier(price: float, min_price: float) -> bool:
    """Price is suspiciously low if >30% below the next cheapest trusted offer."""
    if min_price <= 0:
        return False
    return price < min_price * 0.70


SORT_MODES = {"best_deal", "price_asc", "price_desc", "trust_desc", "delivery_asc"}


def rank_offers(
    offers: list[OfferForRanking],
    buyer_currency: str,
    sort: str = "best_deal",
) -> list[RankedOffer]:
    """Rank offers and assign labels + explanations."""
    if not offers:
        return []

    costs = [o.total_cost for o in offers]
    min_cost = min(costs)
    max_cost = max(costs)

    scored = []
    for offer in offers:
        score = compute_best_deal_score(offer, min_cost, max_cost)
        scored.append((score, offer))

    if sort == "price_asc":
        scored.sort(key=lambda x: x[1].total_cost)
    elif sort == "price_desc":
        scored.sort(key=lambda x: x[1].total_cost, reverse=True)
    elif sort == "trust_desc":
        scored.sort(key=lambda x: x[1].trust_score, reverse=True)
    elif sort == "delivery_asc":
        scored.sort(key=lambda x: x[1].delivery_days or 999)
    else:
        scored.sort(key=lambda x: x[0], reverse=True)

    trusted_offers = [o for _, o in scored if o.trust_score >= 0.60]
    cheapest_trusted = min(trusted_offers, key=lambda o: o.total_cost) if trusted_offers else None

    ranked: list[RankedOffer] = []
    for rank_idx, (score, offer) in enumerate(scored, 1):
        label = _assign_label(offer, rank_idx, scored, cheapest_trusted)
        explanation = _generate_explanation(offer, label, scored, cheapest_trusted, buyer_currency)
        ranked.append(RankedOffer(
            offer_id=offer.offer_id,
            rank=rank_idx,
            score=score,
            label=label,
            explanation=explanation,
            total_cost=offer.cost_breakdown,
        ))

    return ranked


def _assign_label(
    offer: OfferForRanking,
    rank: int,
    scored: list[tuple[float, OfferForRanking]],
    cheapest_trusted: OfferForRanking | None,
) -> str | None:
    if offer.trust_score < 0.30 or offer.red_flags:
        return "risky"
    if rank == 1 and offer.trust_score >= 0.60:
        return "best_deal"
    if cheapest_trusted and offer.offer_id == cheapest_trusted.offer_id and rank != 1:
        return "cheapest"
    return None


def _generate_explanation(
    offer: OfferForRanking,
    label: str | None,
    scored: list[tuple[float, OfferForRanking]],
    cheapest_trusted: OfferForRanking | None,
    currency: str,
) -> str:
    if label == "best_deal":
        if offer.is_domestic:
            shipping = "free shipping" if offer.cost_breakdown.shipping.value == 0 else "shipping included"
            return f"Cheapest total cost from a verified merchant with {shipping}."
        return f"Lowest total cost from {offer.merchant_name} after all import costs."

    if label == "risky":
        count = len(offer.red_flags)
        return f"Unusually low price. {count} risk signal(s) detected. Exercise caution."

    if label == "cheapest" and cheapest_trusted:
        return f"Cheapest verified option at {currency} {offer.total_cost:.2f} total."

    delta = ""
    if cheapest_trusted and offer.total_cost > cheapest_trusted.total_cost:
        diff = offer.total_cost - cheapest_trusted.total_cost
        delta = f"{currency} {diff:.2f} more than cheapest. "

    return f"{delta}{offer.merchant_name} — {currency} {offer.total_cost:.2f} estimated total."
