"""Deep search service: long-running query crawl with progress tracking."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.extractors.base import ExtractedOffer
from app.extractors.digitec import DigitecExtractor, GalaxusExtractor
from app.models.merchant import Merchant
from app.models.offer import Offer, OfferPriceSnapshot
from app.models.product import Product, ProductVariant
from app.offer_visibility import EXCLUDED_OFFER_MERCHANT_SLUGS, EXCLUDED_OFFER_URL_SUBSTRINGS
from app.services.search_service import parse_query_to_filters

MAPPINGS_PATH = Path(__file__).resolve().parents[2] / "seeds" / "digitec_mappings.json"
JOB_TIMEOUT_SECONDS = 30
MIN_RUNTIME_SECONDS = 10
MAX_TRACKED_JOBS = 100
IGNORED_DEEPSEARCH_MERCHANTS = {"digitec-ch", "galaxus-ch"}


@dataclass
class DeepSearchJob:
    id: str
    query: str
    status: str  # queued, running, completed, failed
    progress: int = 0
    scanned_products: int = 0
    total_products: int = 0
    offers_upserted: int = 0
    started_at: str = ""
    completed_at: str | None = None
    message: str = ""
    error: str | None = None
    source_errors: int = 0
    error_samples: list[str] = field(default_factory=list)
    blocked_sources: list[str] = field(default_factory=list)


_jobs: dict[str, DeepSearchJob] = {}
_jobs_lock = asyncio.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extractor_for_slug(slug: str):
    if slug in IGNORED_DEEPSEARCH_MERCHANTS:
        raise ValueError(f"Merchant '{slug}' is ignored in deep search")
    if slug == "galaxus-ch":
        return GalaxusExtractor(lang="de")
    return DigitecExtractor(lang="de")


def _load_mapping_entries() -> list[dict]:
    if not MAPPINGS_PATH.exists():
        return []
    raw = json.loads(MAPPINGS_PATH.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for merchant_slug, entries in raw.items():
        if merchant_slug in IGNORED_DEEPSEARCH_MERCHANTS:
            continue
        for entry in entries:
            rows.append(
                {
                    "merchant_slug": merchant_slug,
                    "product_id": int(entry["digitec_id"]),
                    "variant_key": entry["variant_key"],
                    "product_line": entry["product_line"],
                    "model": entry["model"],
                }
            )
    return rows


def _matches_query(entry: dict, query: str) -> bool:
    parsed = parse_query_to_filters(query)
    text = f"{entry['product_line']} {entry['model']} {entry['variant_key']}".lower()
    q = query.strip().lower()

    if parsed.product_line and parsed.product_line.lower() != str(entry["product_line"]).lower():
        return False
    if parsed.model and parsed.model.lower() not in str(entry["model"]).lower():
        return False
    if parsed.storage and parsed.storage.lower().replace(" ", "") not in str(entry["variant_key"]).lower().replace(" ", ""):
        return False

    if parsed.has_filters:
        return True

    tokens = [t for t in q.replace('"', ' ').split() if len(t) >= 2]
    if not tokens:
        return True
    return all(t in text for t in tokens) or any(t in text for t in tokens)


async def _upsert_offer(
    db: AsyncSession,
    variant: ProductVariant,
    merchant: Merchant,
    ext_offer: ExtractedOffer,
    now: datetime,
) -> int:
    if merchant.slug in EXCLUDED_OFFER_MERCHANT_SLUGS:
        return 0
    for bad in EXCLUDED_OFFER_URL_SUBSTRINGS:
        if bad in ext_offer.product_url:
            return 0

    existing = await db.execute(select(Offer).where(Offer.url == ext_offer.product_url))
    offer = existing.scalar_one_or_none()

    if offer:
        offer.product_variant_id = variant.id
        offer.merchant_id = merchant.id
        offer.raw_title = ext_offer.raw_title
        offer.extracted_attributes = ext_offer.extracted_attributes
        offer.price_amount = ext_offer.price_amount
        offer.price_currency = ext_offer.price_currency
        offer.shipping_cost = ext_offer.shipping_cost or 0.0
        offer.shipping_currency = ext_offer.shipping_currency or "CHF"
        offer.condition = ext_offer.condition
        offer.availability = ext_offer.availability
        offer.delivery_days_min = ext_offer.delivery_days_min
        offer.delivery_days_max = ext_offer.delivery_days_max
        offer.is_active = True
        offer.last_checked = now
        offer.check_count += 1
    else:
        offer = Offer(
            id=uuid.uuid4(),
            product_variant_id=variant.id,
            merchant_id=merchant.id,
            url=ext_offer.product_url,
            raw_title=ext_offer.raw_title,
            extracted_attributes=ext_offer.extracted_attributes,
            identifiers_found=[],
            price_amount=ext_offer.price_amount,
            price_currency=ext_offer.price_currency,
            shipping_cost=ext_offer.shipping_cost or 0.0,
            shipping_currency=ext_offer.shipping_currency or "CHF",
            shipping_source="curated",
            condition=ext_offer.condition,
            availability=ext_offer.availability,
            delivery_days_min=ext_offer.delivery_days_min,
            delivery_days_max=ext_offer.delivery_days_max,
            match_confidence=0.95,
            match_method="deep_search_mapping",
            match_reasons=["deep_search_mapping"],
            mismatch_flags=[],
            review_status="auto_approved",
            is_active=True,
            last_checked=now,
            check_count=1,
        )
        db.add(offer)

    db.add(
        OfferPriceSnapshot(
            id=uuid.uuid4(),
            offer_id=offer.id,
            price_amount=ext_offer.price_amount,
            price_currency=ext_offer.price_currency,
            observed_at=now,
        )
    )
    return 1


async def _run_deep_search(job_id: str) -> None:
    async with _jobs_lock:
        job = _jobs[job_id]
        job.status = "running"
        job.started_at = _now_iso()
        job.message = "Starting deep search..."

    started = datetime.now(timezone.utc)
    entries = _load_mapping_entries()
    job_query = _jobs[job_id].query
    candidates = [e for e in entries if _matches_query(e, job_query)]
    if not candidates:
        candidates = entries

    async with _jobs_lock:
        _jobs[job_id].total_products = len(candidates)

    if not candidates:
        async with _jobs_lock:
            j = _jobs[job_id]
            j.status = "completed"
            j.progress = 100
            j.scanned_products = 0
            j.offers_upserted = 0
            j.completed_at = _now_iso()
            j.message = "No internet deep-search sources connected yet (Digitec/Galaxus excluded)"
        return

    try:
        async with async_session() as db:
            merchant_cache: dict[str, Merchant] = {}
            scanned = 0
            upserted = 0
            failed_sources = 0
            blocked_sources: set[str] = set()

            for entry in candidates:
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                if elapsed > JOB_TIMEOUT_SECONDS:
                    async with _jobs_lock:
                        _jobs[job_id].message = "Timed out at 30s, returning partial results"
                    break

                merchant_slug = entry["merchant_slug"]
                if merchant_slug in blocked_sources:
                    scanned += 1
                    async with _jobs_lock:
                        j = _jobs[job_id]
                        j.scanned_products = scanned
                        j.offers_upserted = upserted
                        j.source_errors = failed_sources
                        j.blocked_sources = sorted(blocked_sources)
                        j.progress = int((scanned / max(1, len(candidates))) * 100)
                        j.message = f"Skipping blocked source(s): {', '.join(sorted(blocked_sources))}"
                    continue

                if merchant_slug not in merchant_cache:
                    m = await db.execute(select(Merchant).where(Merchant.slug == merchant_slug))
                    merchant_cache[merchant_slug] = m.scalar_one_or_none()
                merchant = merchant_cache[merchant_slug]
                if not merchant:
                    scanned += 1
                    continue

                variant_q = await db.execute(
                    select(ProductVariant)
                    .join(Product)
                    .where(
                        Product.product_line == entry["product_line"],
                        Product.model == entry["model"],
                        ProductVariant.variant_key == entry["variant_key"],
                    )
                )
                variant = variant_q.scalar_one_or_none()
                if not variant:
                    scanned += 1
                    continue

                try:
                    extractor = _extractor_for_slug(merchant_slug)
                    offers = await _extract_with_retries(extractor, entry["product_id"])
                    now = datetime.now(timezone.utc)
                    for ext in offers:
                        upserted += await _upsert_offer(db, variant, merchant, ext, now)
                except Exception as exc:
                    failed_sources += 1
                    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 403:
                        blocked_sources.add(merchant_slug)
                    await db.rollback()
                    scanned += 1
                    err = f"{merchant_slug}:{entry['product_id']} {type(exc).__name__}: {str(exc)[:120]}"
                    async with _jobs_lock:
                        j = _jobs[job_id]
                        j.scanned_products = scanned
                        j.offers_upserted = upserted
                        j.source_errors = failed_sources
                        j.blocked_sources = sorted(blocked_sources)
                        if len(j.error_samples) < 5:
                            j.error_samples.append(err)
                        j.progress = int((scanned / max(1, len(candidates))) * 100)
                        j.message = f"Scanned {scanned}/{len(candidates)} products ({failed_sources} source errors)"
                    continue

                await db.commit()
                scanned += 1

                async with _jobs_lock:
                    j = _jobs[job_id]
                    j.scanned_products = scanned
                    j.offers_upserted = upserted
                    j.source_errors = failed_sources
                    j.blocked_sources = sorted(blocked_sources)
                    j.progress = int((scanned / max(1, len(candidates))) * 100)
                    j.message = f"Scanned {scanned}/{len(candidates)} products"

        elapsed_total = (datetime.now(timezone.utc) - started).total_seconds()
        if elapsed_total < MIN_RUNTIME_SECONDS:
            await asyncio.sleep(MIN_RUNTIME_SECONDS - elapsed_total)

        async with _jobs_lock:
            j = _jobs[job_id]
            j.status = "completed"
            j.progress = 100
            j.completed_at = _now_iso()
            if not j.message.startswith("Timed out"):
                suffix = f" with {failed_sources} source errors" if failed_sources else ""
                blocked_suffix = (
                    f" (blocked: {', '.join(j.blocked_sources)})"
                    if j.blocked_sources else ""
                )
                j.message = f"Completed. Updated {j.offers_upserted} offers{suffix}{blocked_suffix}"

    except Exception as exc:
        async with _jobs_lock:
            j = _jobs[job_id]
            j.status = "failed"
            j.error = str(exc)
            j.completed_at = _now_iso()
            j.message = "Deep search failed"


async def _extract_with_retries(extractor: DigitecExtractor | GalaxusExtractor, product_id: int):
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await extractor.extract_offers_by_id(product_id)
        except Exception as exc:  # external source instability
            last_exc = exc
            retryable = True
            if isinstance(exc, httpx.HTTPStatusError):
                status = exc.response.status_code
                retryable = status in (403, 408, 409, 425, 429, 500, 502, 503, 504)
            if not retryable or attempt == 2:
                break
            await asyncio.sleep(0.8 * (attempt + 1))
    if last_exc is not None:
        raise last_exc
    return []


async def start_deep_search(query: str) -> DeepSearchJob:
    job_id = str(uuid.uuid4())
    job = DeepSearchJob(
        id=job_id,
        query=query,
        status="queued",
        progress=0,
        started_at=_now_iso(),
        message="Queued",
    )

    async with _jobs_lock:
        _jobs[job_id] = job
        if len(_jobs) > MAX_TRACKED_JOBS:
            oldest = sorted(_jobs.values(), key=lambda x: x.started_at)[: len(_jobs) - MAX_TRACKED_JOBS]
            for o in oldest:
                _jobs.pop(o.id, None)

    asyncio.create_task(_run_deep_search(job_id))
    return job


async def get_deep_search_job(job_id: str) -> DeepSearchJob | None:
    async with _jobs_lock:
        return _jobs.get(job_id)


def deep_search_job_to_dict(job: DeepSearchJob) -> dict:
    return asdict(job)
