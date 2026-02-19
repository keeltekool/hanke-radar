"""Enrich procurement records with data from the RHR JSON API.

The riigihanked.riik.ee portal is an Angular SPA. The real data comes from
JSON API endpoints, not static HTML. We use:
- /procurement/{rhr_id}/latest-version — maps to version ID
- /proc-vers/{versionId}/general-info — contact person name
- /proc-vers/{versionId}/additional-data — address, contact details from free text

The rhr_id is an internal integer ID extracted from CallForTendersDocumentReference
URIs in the eForms XML bulk dump.
"""

import asyncio
import re
import time
from datetime import UTC, datetime

import httpx
from sqlalchemy import select, update

from hanke_radar.config import settings
from hanke_radar.db.engine import async_session
from hanke_radar.db.models import Procurement, ScrapeRun


async def _fetch_json(client: httpx.AsyncClient, url: str) -> dict | None:
    """Fetch a JSON endpoint, return None on any error."""
    try:
        resp = await client.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def _extract_contact_from_text(text: str) -> dict:
    """Extract phone numbers and emails from free text (additionalInfo field)."""
    result = {}

    # Email patterns
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if emails:
        result["contact_email"] = emails[0]

    # Estonian phone patterns: +372 XXXX XXXX, 5XX XXXX, etc.
    phones = re.findall(r"(?:\+372\s?)?(?:\d[\s-]?){7,8}", text)
    if phones:
        result["contact_phone"] = phones[0].strip()

    return result


async def enrich_procurement(
    client: httpx.AsyncClient,
    procurement: Procurement,
    verbose: bool = True,
) -> dict | None:
    """Fetch additional data for a single procurement from the RHR API.

    Uses the rhr_id (internal integer ID) to access the API.
    Returns a dict of enrichment fields, or None if enrichment failed.
    """
    rhr_id = procurement.rhr_id
    if not rhr_id:
        return None

    base = settings.riigihanked_base_url

    # Step 1: Get latest version ID
    version_data = await _fetch_json(client, f"{base}/procurement/{rhr_id}/latest-version")
    if not version_data:
        if verbose:
            print(f"  No version data for rhr_id={rhr_id}")
        return None

    version_id = None
    if isinstance(version_data, dict):
        version_id = version_data.get("value") or version_data.get("procurementVersionId")

    if not version_id:
        if verbose:
            print(f"  Could not extract version ID for rhr_id={rhr_id}")
        return None

    enrichment = {}

    # Step 2: Get contact person from general-info
    general = await _fetch_json(client, f"{base}/proc-vers/{version_id}/general-info")
    if general:
        liable_person = general.get("liablePersonName", "")
        if liable_person:
            enrichment["contact_person"] = liable_person

    # Step 3: Get address and contact details from additional-data
    additional = await _fetch_json(client, f"{base}/proc-vers/{version_id}/additional-data")
    if additional:
        # Performance address from procPart.place (skip generic country-only values)
        proc_part = additional.get("procPart", {})
        place = proc_part.get("place", "")
        if isinstance(place, str) and place.strip():
            place_clean = place.strip()
            # Only store if more specific than just a country name
            if len(place_clean) > 10 and place_clean.lower() not in ("eesti", "estonia"):
                enrichment["performance_address"] = place_clean

        # Contact details from free text (procObject.additionalInfo)
        proc_obj = additional.get("procObject", {})
        additional_info = proc_obj.get("additionalInfo", "")
        if additional_info:
            contact_from_text = _extract_contact_from_text(additional_info)
            enrichment.update(contact_from_text)

    return enrichment if enrichment else None


async def enrich_active_procurements(
    limit: int = 50,
    verbose: bool = True,
) -> dict:
    """Enrich active procurements that haven't been enriched yet.

    Returns a summary dict.
    """
    if async_session is None:
        raise RuntimeError("DATABASE_URL not configured")

    start_time = time.monotonic()
    enriched_count = 0
    skipped = 0
    errors = 0

    async with async_session() as session:
        # Record the scrape run
        run = ScrapeRun(run_type="notice_html")
        session.add(run)
        await session.commit()

        # Get active procurements not yet enriched (with rhr_id)
        result = await session.execute(
            select(Procurement)
            .where(Procurement.status == "active")
            .where(Procurement.enriched_at.is_(None))
            .where(Procurement.rhr_id.isnot(None))
            .order_by(Procurement.submission_deadline.asc())  # soonest deadline first
            .limit(limit)
        )
        procurements = result.scalars().all()

        if verbose:
            print(f"Found {len(procurements)} procurements to enrich")

        async with httpx.AsyncClient() as client:
            for proc in procurements:
                try:
                    enrichment = await enrich_procurement(client, proc, verbose)
                    if enrichment:
                        update_dict = {"enriched_at": datetime.now(UTC)}
                        for key in ("contact_person", "contact_email", "contact_phone",
                                    "performance_address"):
                            if key in enrichment:
                                update_dict[key] = enrichment[key]

                        await session.execute(
                            update(Procurement)
                            .where(Procurement.id == proc.id)
                            .values(**update_dict)
                        )
                        enriched_count += 1
                        if verbose:
                            print(f"  Enriched: {proc.title[:60]}")
                    else:
                        # Mark as attempted so we don't retry indefinitely
                        await session.execute(
                            update(Procurement)
                            .where(Procurement.id == proc.id)
                            .values(enriched_at=datetime.now(UTC))
                        )
                        skipped += 1
                except Exception as e:
                    errors += 1
                    if verbose:
                        print(f"  Error enriching {proc.notice_id}: {e}")

                # Polite rate limiting
                await asyncio.sleep(settings.scrape_delay_seconds)

            await session.commit()

        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Update run record
        run.notices_found = len(procurements)
        run.notices_stored = enriched_count
        run.notices_skipped = skipped
        run.errors = errors
        run.duration_ms = duration_ms
        run.status = "completed"
        await session.commit()

        summary = {
            "total": len(procurements),
            "enriched": enriched_count,
            "skipped": skipped,
            "errors": errors,
            "duration_ms": duration_ms,
        }

        if verbose:
            print(f"\nDone: {enriched_count} enriched, {skipped} skipped, {errors} errors")
            print(f"Duration: {duration_ms}ms")

        return summary
