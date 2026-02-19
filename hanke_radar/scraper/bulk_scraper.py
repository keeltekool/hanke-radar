"""Bulk XML scraper for riigihanked.riik.ee monthly dumps."""

import time
from datetime import UTC, datetime

import httpx
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hanke_radar.config import settings
from hanke_radar.db.engine import async_session
from hanke_radar.db.models import Procurement, ScrapeRun, TradeCpvMapping
from hanke_radar.db.seed import TRADE_CPV_SEEDS
from hanke_radar.scraper.cpv_filter import get_trade_tags, is_trade_relevant
from hanke_radar.scraper.xml_parser import ParsedProcurement, is_active_tender, parse_bulk_xml

# NUTS code to human-readable Estonian region names
NUTS_NAMES = {
    "EE001": "Põhja-Eesti",
    "EE004": "Lääne-Eesti",
    "EE006": "Kesk-Eesti",
    "EE007": "Kirde-Eesti",
    "EE008": "Lõuna-Eesti",
    "EE009": "Kesk-Eesti",  # alternate
    "EEZZZ": "Eesti (täpsustamata)",
}

# Procedure code to human-readable names
PROCEDURE_NAMES = {
    "open": "Avatud hankemenetlus",
    "oth-single": "Lihthange",
    "restricted": "Piiratud hankemenetlus",
    "neg-w-call": "Läbirääkimistega hankemenetlus",
    "innovation": "Innovatsioonipartnerlus",
    "comp-dial": "Võistlev dialoog",
    "neg-wo-call": "Otseost",
}


def _derive_contract_type(cpv_primary: str) -> str:
    """Derive contract type from primary CPV code."""
    if not cpv_primary:
        return "unknown"
    prefix = cpv_primary[:2]
    if prefix == "45":
        return "ehitustööd"  # Construction works
    elif prefix in (
        "50", "51", "55", "60", "63", "64", "65", "66", "70",
        "71", "72", "73", "75", "76", "77", "79", "80", "85", "90", "92", "98",
    ):
        return "teenused"  # Services
    else:
        return "tarned"  # Supplies


async def _ensure_trade_mappings(session: AsyncSession) -> None:
    """Sync trade_cpv_mappings table with seed data (adds new prefixes on each run)."""
    existing = await session.execute(select(TradeCpvMapping.cpv_prefix))
    existing_prefixes = {row[0] for row in existing.all()}

    added = 0
    for seed in TRADE_CPV_SEEDS:
        if seed["cpv_prefix"] not in existing_prefixes:
            session.add(TradeCpvMapping(**seed))
            added += 1

    if added:
        await session.commit()


def _to_db_dict(p: ParsedProcurement) -> dict:
    """Convert a ParsedProcurement to a dict for DB insertion."""
    all_cpvs = [p.cpv_primary] + p.cpv_additional if p.cpv_primary else p.cpv_additional
    trade_tags = get_trade_tags(all_cpvs)

    return {
        "notice_id": p.notice_id,
        "procurement_id": p.procurement_id,
        "rhr_id": p.rhr_id,
        "title": p.title,
        "description": p.description,
        "contracting_auth": p.contracting_auth,
        "contracting_auth_reg": p.contracting_auth_reg,
        "contract_type": _derive_contract_type(p.cpv_primary),
        "procedure_type": PROCEDURE_NAMES.get(p.procedure_type, p.procedure_type),
        "cpv_primary": p.cpv_primary,
        "cpv_additional": p.cpv_additional,
        "estimated_value": p.estimated_value,
        "nuts_code": p.nuts_code,
        "nuts_name": NUTS_NAMES.get(p.nuts_code, ""),
        "submission_deadline": p.submission_deadline,
        "publication_date": p.publication_date,
        "duration_months": p.duration_months,
        "status": "active",
        "source_url": p.source_url,
        "trade_tags": trade_tags,
    }


async def scrape_month(year: int, month: int, verbose: bool = True) -> dict:
    """Scrape a single month's bulk XML from riigihanked and store trade-relevant notices.

    Returns a summary dict with counts.
    """
    if async_session is None:
        raise RuntimeError("DATABASE_URL not configured")

    year_month = f"{year}-{month:02d}"
    url = f"{settings.riigihanked_base_url}/opendata/notice/{year}/month/{month}/xml"

    start_time = time.monotonic()

    async with async_session() as session:
        # Record the scrape run
        run = ScrapeRun(run_type="bulk_xml", year_month=year_month)
        session.add(run)
        await session.commit()

        await _ensure_trade_mappings(session)

        try:
            # Download the bulk XML
            if verbose:
                print(f"Downloading {url}...")
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.get(url)
                response.raise_for_status()

            xml_bytes = response.content
            if verbose:
                print(f"Downloaded {len(xml_bytes) / 1024 / 1024:.1f} MB")

            # Parse all notices from XML
            all_notices = parse_bulk_xml(xml_bytes)
            run.notices_found = len(all_notices)
            if verbose:
                print(f"Parsed {len(all_notices)} total notices")

            # Filter: active tenders with trade-relevant CPV codes
            relevant = []
            for notice in all_notices:
                if not is_active_tender(notice):
                    continue
                all_cpvs = [notice.cpv_primary] + notice.cpv_additional
                if any(is_trade_relevant(cpv) for cpv in all_cpvs if cpv):
                    relevant.append(notice)

            if verbose:
                print(f"Filtered to {len(relevant)} trade-relevant active tenders")

            # Upsert into database
            stored = 0
            errors = 0
            for notice in relevant:
                try:
                    db_dict = _to_db_dict(notice)
                    stmt = (
                        pg_insert(Procurement)
                        .values(**db_dict)
                        .on_conflict_do_update(
                            index_elements=["notice_id"],
                            set_={
                                "rhr_id": db_dict["rhr_id"],
                                "title": db_dict["title"],
                                "description": db_dict["description"],
                                "estimated_value": db_dict["estimated_value"],
                                "submission_deadline": db_dict["submission_deadline"],
                                "status": db_dict["status"],
                                "source_url": db_dict["source_url"],
                                "trade_tags": db_dict["trade_tags"],
                                "updated_at": datetime.now(UTC),
                            },
                        )
                    )
                    await session.execute(stmt)
                    stored += 1
                except Exception as e:
                    errors += 1
                    if verbose:
                        print(f"  Error storing {notice.notice_id}: {e}")

            await session.commit()

            # Update run record
            duration_ms = int((time.monotonic() - start_time) * 1000)
            run.notices_stored = stored
            run.notices_skipped = run.notices_found - len(relevant)
            run.errors = errors
            run.duration_ms = duration_ms
            run.status = "completed"
            await session.commit()

            summary = {
                "year_month": year_month,
                "total_notices": run.notices_found,
                "trade_relevant": len(relevant),
                "stored": stored,
                "skipped": run.notices_skipped,
                "errors": errors,
                "duration_ms": duration_ms,
            }

            if verbose:
                print(f"Done: {stored} stored, {run.notices_skipped} skipped, {errors} errors")
                print(f"Duration: {duration_ms}ms")

            return summary

        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)[:500]
            run.duration_ms = int((time.monotonic() - start_time) * 1000)
            await session.commit()
            raise


async def update_expired_procurements(verbose: bool = True) -> int:
    """Mark procurements past their submission deadline as expired."""
    if async_session is None:
        raise RuntimeError("DATABASE_URL not configured")

    async with async_session() as session:
        result = await session.execute(
            text("""
                UPDATE procurements
                SET status = 'expired', updated_at = NOW()
                WHERE status = 'active'
                  AND submission_deadline IS NOT NULL
                  AND submission_deadline < NOW()
            """)
        )
        await session.commit()
        count = result.rowcount
        if verbose:
            print(f"Marked {count} procurements as expired")
        return count
