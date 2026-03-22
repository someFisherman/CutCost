"""Deep search service: long-running query crawl with progress tracking."""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from selectolax.parser import HTMLParser
from sqlalchemy import func, select
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
    job_query = _jobs[job_id].query
    search_urls = await _search_web_urls(job_query, limit=24)

    async with _jobs_lock:
        _jobs[job_id].total_products = len(search_urls)

    if not search_urls:
        async with _jobs_lock:
            j = _jobs[job_id]
            j.status = "completed"
            j.progress = 100
            j.scanned_products = 0
            j.offers_upserted = 0
            j.completed_at = _now_iso()
            j.message = "No web results found for this query"
        return

    try:
        async with async_session() as db:
            variant = await _best_variant_for_query(db, job_query)
            if not variant:
                async with _jobs_lock:
                    j = _jobs[job_id]
                    j.status = "completed"
                    j.progress = 100
                    j.completed_at = _now_iso()
                    j.message = "No catalog product match for query. Use guided search to specify brand/model."
                return

            scanned = 0
            upserted = 0
            failed_sources = 0
            blocked_sources: set[str] = set()
            seen_domains: set[str] = set()
            query_tokens = [t for t in re.split(r"\s+", job_query.lower()) if len(t) >= 2]

            for candidate_url in search_urls:
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                if elapsed > JOB_TIMEOUT_SECONDS:
                    async with _jobs_lock:
                        _jobs[job_id].message = "Timed out at 30s, returning partial results"
                    break

                parsed = urlparse(candidate_url)
                domain = (parsed.hostname or "").lower().replace("www.", "")
                if not domain:
                    scanned += 1
                    continue
                if domain in blocked_sources:
                    scanned += 1
                    continue

                try:
                    snapshot = await _fetch_page_snapshot(candidate_url)
                    if snapshot is None:
                        failed_sources += 1
                        blocked_sources.add(domain)
                        scanned += 1
                        continue

                    title = snapshot["title"]
                    text = snapshot["text"]
                    relevance = _match_relevance(query_tokens, title, text)
                    if relevance < 0.4:
                        scanned += 1
                        continue

                    merchant = await _get_or_create_merchant(db, snapshot["url"])
                    if not merchant:
                        scanned += 1
                        continue

                    if domain in seen_domains and relevance < 0.7:
                        scanned += 1
                        continue
                    seen_domains.add(domain)

                    if snapshot["price"] is None:
                        scanned += 1
                        continue

                    now = datetime.now(timezone.utc)
                    ext = ExtractedOffer(
                        raw_title=title,
                        price_amount=float(snapshot["price"]),
                        price_currency=snapshot["currency"] or merchant.currency,
                        product_url=snapshot["url"],
                        availability="in_stock",
                        condition="new",
                        shipping_cost=0.0,
                        shipping_currency=merchant.currency,
                        extracted_attributes={
                            "source": "internet_search",
                            "domain": domain,
                            "relevance": relevance,
                        },
                    )
                    upserted += await _upsert_offer(db, variant, merchant, ext, now)
                except Exception as exc:
                    failed_sources += 1
                    blocked_sources.add(domain)
                    await db.rollback()
                    scanned += 1
                    err = f"{domain} {type(exc).__name__}: {str(exc)[:140]}"
                    async with _jobs_lock:
                        j = _jobs[job_id]
                        j.scanned_products = scanned
                        j.offers_upserted = upserted
                        j.source_errors = failed_sources
                        j.blocked_sources = sorted(blocked_sources)
                        if len(j.error_samples) < 5:
                            j.error_samples.append(err)
                        j.progress = int((scanned / max(1, len(search_urls))) * 100)
                        j.message = f"Scanned {scanned}/{len(search_urls)} pages ({failed_sources} source errors)"
                    continue

                await db.commit()
                scanned += 1

                async with _jobs_lock:
                    j = _jobs[job_id]
                    j.scanned_products = scanned
                    j.offers_upserted = upserted
                    j.source_errors = failed_sources
                    j.blocked_sources = sorted(blocked_sources)
                    j.progress = int((scanned / max(1, len(search_urls))) * 100)
                    j.message = f"Scanned {scanned}/{len(search_urls)} pages"

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


async def _search_web_urls(query: str, limit: int = 20) -> list[str]:
    """Run a generic web search and return candidate product URLs."""
    search_query = f"{query} buy price shop"
    endpoints = [
        ("https://html.duckduckgo.com/html/", {"q": search_query}),
        ("https://duckduckgo.com/html/", {"q": search_query}),
    ]
    urls: list[str] = []
    for endpoint, params in endpoints:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(endpoint, params=params, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                tree = HTMLParser(resp.text)
                links = tree.css("a.result__a")
                for node in links:
                    href = node.attributes.get("href", "")
                    if not href:
                        continue
                    if "duckduckgo.com/l/?" in href and "uddg=" in href:
                        parsed = urlparse(href)
                        uddg = parse_qs(parsed.query).get("uddg", [""])[0]
                        href = unquote(uddg) if uddg else href
                    if not href.startswith("http"):
                        continue
                    host = (urlparse(href).hostname or "").lower()
                    if not host or "duckduckgo.com" in host:
                        continue
                    urls.append(href)
                    if len(urls) >= limit:
                        break
        except Exception:
            continue
        if urls:
            break
    # Keep insertion order unique
    deduped: list[str] = []
    seen: set[str] = set()
    for u in urls:
        if u not in seen:
            deduped.append(u)
            seen.add(u)
    return deduped[:limit]


async def _best_variant_for_query(db: AsyncSession, query: str) -> ProductVariant | None:
    q = query.strip()
    if not q:
        return None
    res = await db.execute(
        select(ProductVariant)
        .join(Product)
        .where(
            func.similarity(ProductVariant.display_name, q) > 0.08
        )
        .order_by(func.similarity(ProductVariant.display_name, q).desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


def _match_relevance(tokens: list[str], title: str, text: str) -> float:
    if not tokens:
        return 0.0
    haystack = f"{title} {text[:4000]}".lower()
    hits = sum(1 for t in tokens if t in haystack)
    return hits / max(1, len(tokens))


def _extract_price_and_currency(text: str) -> tuple[float | None, str | None]:
    patterns = [
        r"(CHF|EUR|USD|€|\$|Fr\.?)\s*([0-9]{1,3}(?:[ '\.,][0-9]{3})*(?:[,\.\s][0-9]{2})?)",
        r"([0-9]{1,3}(?:[ '\.,][0-9]{3})*(?:[,\.\s][0-9]{2})?)\s*(CHF|EUR|USD|€|\$|Fr\.?)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if not m:
            continue
        a, b = m.group(1), m.group(2)
        if a.upper() in {"CHF", "EUR", "USD", "€", "$", "FR."}:
            cur_raw, amount_raw = a, b
        else:
            amount_raw, cur_raw = a, b
        amount_norm = amount_raw.replace("'", "").replace(" ", "").replace(",", ".")
        amount_norm = re.sub(r"(?<=\d)\.(?=\d{3}(?:\D|$))", "", amount_norm)
        try:
            value = float(amount_norm)
        except ValueError:
            continue
        cur_map = {"€": "EUR", "$": "USD", "FR.": "CHF", "FR": "CHF"}
        currency = cur_map.get(cur_raw.upper(), cur_raw.upper())
        if value <= 0:
            continue
        return value, currency
    return None, None


async def _fetch_page_snapshot(url: str) -> dict | None:
    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code >= 400:
            return None
        ctype = (resp.headers.get("content-type") or "").lower()
        if "text/html" not in ctype:
            return None
        html = resp.text
        tree = HTMLParser(html)
        title_node = tree.css_first("title")
        title = title_node.text(strip=True) if title_node else ""
        body_text = tree.body.text(separator=" ", strip=True) if tree.body else ""
        price, currency = _extract_price_and_currency(f"{title}\n{body_text[:12000]}")
        return {
            "url": str(resp.url),
            "title": title,
            "text": body_text,
            "price": price,
            "currency": currency,
        }


async def _get_or_create_merchant(db: AsyncSession, url: str) -> Merchant | None:
    host = (urlparse(url).hostname or "").lower().replace("www.", "")
    if not host:
        return None
    slug = re.sub(r"[^a-z0-9]+", "-", host).strip("-")[:100]
    existing = await db.execute(select(Merchant).where(Merchant.slug == slug))
    merchant = existing.scalar_one_or_none()
    if merchant:
        return merchant
    tld = host.split(".")[-1] if "." in host else ""
    country_map = {"ch": "CH", "de": "DE", "at": "AT", "fr": "FR", "it": "IT", "com": "US"}
    currency_map = {"CH": "CHF", "DE": "EUR", "AT": "EUR", "FR": "EUR", "IT": "EUR", "US": "USD"}
    country = country_map.get(tld, "DE")
    currency = currency_map.get(country, "EUR")
    merchant = Merchant(
        id=uuid.uuid4(),
        slug=slug,
        name=host,
        website=f"https://{host}",
        country=country,
        currency=currency,
        is_marketplace=False,
        is_active=True,
        is_curated=False,
        affiliate_config={},
        extraction_config={"source": "internet_search"},
        notes="Auto-created from deep internet search",
    )
    db.add(merchant)
    await db.flush()
    return merchant


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
