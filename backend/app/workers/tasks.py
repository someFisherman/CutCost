"""Background task implementations."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.crawl import CrawlJob, ExtractionResult
from app.models.merchant import Merchant
from app.models.offer import Offer, OfferPriceSnapshot
from app.services.matching_service import match_offer

logger = logging.getLogger(__name__)

EXTRACTOR_MAP: dict[str, type] = {}


def _load_extractors() -> None:
    global EXTRACTOR_MAP
    if EXTRACTOR_MAP:
        return
    from app.extractors.digitec import DigitecExtractor, GalaxusExtractor
    EXTRACTOR_MAP = {
        "digitec-ch": DigitecExtractor,
        "galaxus-ch": GalaxusExtractor,
    }


async def execute_pending_crawl_jobs(db: AsyncSession) -> int:
    """Process all pending crawl jobs. Returns count of jobs processed."""
    _load_extractors()

    result = await db.execute(
        select(CrawlJob)
        .where(CrawlJob.status == "pending")
        .where(CrawlJob.retry_count < CrawlJob.max_retries)
        .order_by(CrawlJob.priority.asc(), CrawlJob.scheduled_at.asc())
        .limit(50)
        .options(selectinload(CrawlJob.merchant_id))  # type: ignore[arg-type]
    )
    jobs = result.scalars().all()

    processed = 0
    for job in jobs:
        await _execute_single_job(db, job)
        processed += 1

    return processed


async def _execute_single_job(db: AsyncSession, job: CrawlJob) -> None:
    merchant = await db.get(Merchant, job.merchant_id)
    if not merchant or not merchant.is_active:
        job.status = "cancelled"
        await db.commit()
        return

    extractor_cls = EXTRACTOR_MAP.get(merchant.slug)
    if not extractor_cls:
        logger.warning("No extractor for merchant %s", merchant.slug)
        job.status = "failed"
        job.error_message = f"No extractor registered for {merchant.slug}"
        job.error_category = "no_extractor"
        await db.commit()
        return

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        extractor = extractor_cls()
        extracted = await extractor.extract_offer(job.url)

        if not extracted:
            job.status = "failed"
            job.error_message = "Extraction returned no data"
            job.error_category = "empty_result"
            job.retry_count += 1
            await db.commit()
            return

        extraction = ExtractionResult(
            crawl_job_id=job.id,
            raw_data=extracted.raw_data,
            extracted_title=extracted.raw_title,
            extracted_price=extracted.price_amount,
            extracted_currency=extracted.price_currency,
            extracted_ean=extracted.ean,
            extracted_availability=extracted.availability,
            parsing_method="api" if merchant.slug in ("digitec-ch", "galaxus-ch") else "html",
        )
        db.add(extraction)

        identifiers = []
        if extracted.ean:
            identifiers.append({"type": "ean", "value": extracted.ean})
        if extracted.mpn:
            identifiers.append({"type": "mpn", "value": extracted.mpn})
        if extracted.asin:
            identifiers.append({"type": "asin", "value": extracted.asin})

        match_result = await match_offer(
            db, identifiers, extracted.extracted_attributes,
            extracted.brand, extracted.model,
        )

        existing = await db.execute(
            select(Offer).where(Offer.url == extracted.product_url)
        )
        offer = existing.scalar_one_or_none()

        if offer:
            old_price = float(offer.price_amount)
            offer.price_amount = extracted.price_amount
            offer.price_currency = extracted.price_currency
            offer.raw_title = extracted.raw_title
            offer.availability = extracted.availability
            offer.condition = extracted.condition
            offer.identifiers_found = identifiers
            offer.extracted_attributes = extracted.extracted_attributes
            offer.last_checked = datetime.now(timezone.utc)
            offer.check_count += 1

            if abs(old_price - extracted.price_amount) > 0.01:
                offer.last_price_change = datetime.now(timezone.utc)
                db.add(OfferPriceSnapshot(
                    offer_id=offer.id,
                    price_amount=extracted.price_amount,
                    price_currency=extracted.price_currency,
                    availability=extracted.availability,
                ))

            if match_result.variant_id:
                offer.product_variant_id = match_result.variant_id
                offer.match_confidence = match_result.confidence
                offer.match_method = match_result.method
                offer.match_reasons = match_result.reasons
                offer.mismatch_flags = match_result.mismatch_flags
        else:
            offer = Offer(
                product_variant_id=match_result.variant_id,
                merchant_id=merchant.id,
                url=extracted.product_url,
                raw_title=extracted.raw_title,
                price_amount=extracted.price_amount,
                price_currency=extracted.price_currency,
                condition=extracted.condition,
                availability=extracted.availability,
                identifiers_found=identifiers,
                extracted_attributes=extracted.extracted_attributes,
                match_confidence=match_result.confidence,
                match_method=match_result.method,
                match_reasons=match_result.reasons,
                mismatch_flags=match_result.mismatch_flags,
                shipping_cost=extracted.shipping_cost,
                shipping_currency=extracted.shipping_currency,
                delivery_days_min=extracted.delivery_days_min,
                delivery_days_max=extracted.delivery_days_max,
            )
            db.add(offer)

            db.add(OfferPriceSnapshot(
                offer_id=offer.id,
                price_amount=extracted.price_amount,
                price_currency=extracted.price_currency,
                availability=extracted.availability,
            ))

        extraction.offer_id = offer.id
        job.status = "success"
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()

    except Exception as exc:
        logger.exception("Crawl job %s failed", job.id)
        job.status = "failed"
        job.error_message = str(exc)[:500]
        job.error_category = "exception"
        job.retry_count += 1
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
