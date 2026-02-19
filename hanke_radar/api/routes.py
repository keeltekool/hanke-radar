"""API routes for procurement data."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from hanke_radar.db.engine import get_session
from hanke_radar.db.models import Procurement, ScrapeRun

router = APIRouter()


@router.get("/procurements")
async def list_procurements(
    trade: str | None = Query(None, description="Filter by trade tag (plumbing, electrical, etc.)"),
    cpv: str | None = Query(None, description="Filter by CPV code prefix"),
    region: str | None = Query(None, description="Filter by NUTS region code"),
    status: str = Query("active", description="Filter by status (active, expired, awarded)"),
    min_value: float | None = Query(None, description="Minimum estimated value EUR"),
    max_value: float | None = Query(None, description="Maximum estimated value EUR"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """List procurements with filtering and pagination."""
    query = select(Procurement)

    if status:
        query = query.where(Procurement.status == status)
    if trade:
        query = query.where(Procurement.trade_tags.any(trade))
    if cpv:
        query = query.where(Procurement.cpv_primary.startswith(cpv))
    if region:
        query = query.where(Procurement.nuts_code == region)
    if min_value is not None:
        query = query.where(Procurement.estimated_value >= min_value)
    if max_value is not None:
        query = query.where(Procurement.estimated_value <= max_value)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate, newest first
    query = (
        query.order_by(Procurement.publication_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(query)
    rows = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [_serialize(r) for r in rows],
    }


@router.get("/procurements/stats")
async def procurement_stats(
    session: AsyncSession = Depends(get_session),
):
    """Get procurement counts by trade, region, and status."""
    # By trade
    trade_result = await session.execute(
        text("""
            SELECT unnest(trade_tags) as trade, COUNT(*) as cnt
            FROM procurements
            WHERE status = 'active'
            GROUP BY trade ORDER BY cnt DESC
        """)
    )
    # By region
    region_result = await session.execute(
        select(Procurement.nuts_code, Procurement.nuts_name, func.count(Procurement.id))
        .where(Procurement.status == "active")
        .group_by(Procurement.nuts_code, Procurement.nuts_name)
        .order_by(func.count(Procurement.id).desc())
    )
    # By status
    status_result = await session.execute(
        select(Procurement.status, func.count(Procurement.id)).group_by(Procurement.status)
    )

    return {
        "by_trade": [{"trade": t, "count": c} for t, c in trade_result.all()],
        "by_region": [
            {"nuts_code": n, "nuts_name": name, "count": c}
            for n, name, c in region_result.all()
        ],
        "by_status": [{"status": s, "count": c} for s, c in status_result.all()],
    }


@router.get("/procurements/{procurement_id}")
async def get_procurement(
    procurement_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single procurement by database ID."""
    result = await session.execute(select(Procurement).where(Procurement.id == procurement_id))
    row = result.scalar()
    if row is None:
        return {"error": "Not found"}, 404
    return _serialize(row)


@router.get("/trades")
async def list_trades(
    session: AsyncSession = Depends(get_session),
):
    """List available trade categories with procurement counts."""
    result = await session.execute(
        text("""
            SELECT unnest(trade_tags) as trade, COUNT(*) as cnt
            FROM procurements
            GROUP BY trade ORDER BY cnt DESC
        """)
    )
    return [{"trade_key": t, "count": c} for t, c in result.all()]


@router.get("/scrape/status")
async def scrape_status(
    session: AsyncSession = Depends(get_session),
):
    """Get the last scrape run info."""
    result = await session.execute(select(ScrapeRun).order_by(ScrapeRun.id.desc()).limit(5))
    runs = result.scalars().all()
    return [
        {
            "id": r.id,
            "run_type": r.run_type,
            "year_month": r.year_month,
            "status": r.status,
            "notices_found": r.notices_found,
            "notices_stored": r.notices_stored,
            "errors": r.errors,
            "duration_ms": r.duration_ms,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]


def _serialize(p: Procurement) -> dict:
    """Serialize a Procurement ORM object to a dict."""
    return {
        "id": p.id,
        "notice_id": p.notice_id,
        "procurement_id": p.procurement_id,
        "title": p.title,
        "description": p.description,
        "contracting_auth": p.contracting_auth,
        "contracting_auth_reg": p.contracting_auth_reg,
        "contract_type": p.contract_type,
        "procedure_type": p.procedure_type,
        "cpv_primary": p.cpv_primary,
        "cpv_additional": p.cpv_additional,
        "estimated_value": float(p.estimated_value) if p.estimated_value else None,
        "nuts_code": p.nuts_code,
        "nuts_name": p.nuts_name,
        "submission_deadline": p.submission_deadline.isoformat() if p.submission_deadline else None,
        "publication_date": p.publication_date.isoformat() if p.publication_date else None,
        "duration_months": p.duration_months,
        "status": p.status,
        "source_url": p.source_url,
        "trade_tags": p.trade_tags,
        "contact_person": p.contact_person,
        "contact_email": p.contact_email,
        "contact_phone": p.contact_phone,
        "performance_address": p.performance_address,
    }
