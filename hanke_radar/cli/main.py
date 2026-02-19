"""HankeRadar CLI — scrape and manage procurement data."""

import asyncio
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="hanke", help="HankeRadar — Estonian public procurement scraper")
console = Console()


@app.command()
def scrape(
    year: int = typer.Option(datetime.now().year, help="Year to scrape"),
    month: int = typer.Option(datetime.now().month, help="Month to scrape"),
    backfill: int = typer.Option(0, help="Number of previous months to also scrape"),
):
    """Scrape procurement data from riigihanked.riik.ee bulk XML."""
    from hanke_radar.scraper.bulk_scraper import scrape_month

    months_to_scrape = []
    for i in range(backfill, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        months_to_scrape.append((y, m))

    console.print(f"[bold]Scraping {len(months_to_scrape)} month(s)...[/bold]")

    async def _scrape_all():
        """Run all months in a single event loop to avoid session/engine issues."""
        _results = []
        for _y, _m in months_to_scrape:
            console.print(f"\n[cyan]--- {_y}-{_m:02d} ---[/cyan]")
            try:
                summary = await scrape_month(_y, _m)
                _results.append(summary)
            except Exception as e:
                console.print(f"[red]Failed: {e}[/red]")
        return _results

    results = asyncio.run(_scrape_all())

    if results:
        console.print("\n[bold green]Summary:[/bold green]")
        table = Table()
        table.add_column("Month")
        table.add_column("Total", justify="right")
        table.add_column("Relevant", justify="right")
        table.add_column("Stored", justify="right")
        table.add_column("Errors", justify="right")
        table.add_column("Time", justify="right")

        for r in results:
            table.add_row(
                r["year_month"],
                str(r["total_notices"]),
                str(r["trade_relevant"]),
                str(r["stored"]),
                str(r["errors"]),
                f"{r['duration_ms']}ms",
            )
        console.print(table)


@app.command()
def expire():
    """Mark procurements past their deadline as expired."""
    from hanke_radar.scraper.bulk_scraper import update_expired_procurements

    count = asyncio.run(update_expired_procurements())
    console.print(f"[green]Marked {count} procurements as expired[/green]")


@app.command()
def status():
    """Show database stats and last scrape run info."""
    from hanke_radar.db.engine import async_session

    async def _status():
        if async_session is None:
            console.print("[red]DATABASE_URL not configured[/red]")
            return

        from sqlalchemy import func, select, text

        from hanke_radar.db.models import Procurement, ScrapeRun

        async with async_session() as session:
            # Total procurements
            total = await session.execute(select(func.count(Procurement.id)))
            total_count = total.scalar()

            # By status
            by_status = await session.execute(
                select(Procurement.status, func.count(Procurement.id)).group_by(Procurement.status)
            )
            status_counts = dict(by_status.all())

            # By trade tag
            trade_counts = await session.execute(
                text("""
                    SELECT unnest(trade_tags) as trade, COUNT(*) as cnt
                    FROM procurements
                    GROUP BY trade
                    ORDER BY cnt DESC
                """)
            )
            trades = trade_counts.all()

            # Last scrape run
            last_run = await session.execute(
                select(ScrapeRun).order_by(ScrapeRun.id.desc()).limit(1)
            )
            last = last_run.scalar()

            console.print("\n[bold]HankeRadar Database Status[/bold]")
            console.print(f"Total procurements: [cyan]{total_count}[/cyan]")

            if status_counts:
                table = Table(title="By Status")
                table.add_column("Status")
                table.add_column("Count", justify="right")
                for s, c in status_counts.items():
                    table.add_row(s, str(c))
                console.print(table)

            if trades:
                table = Table(title="By Trade")
                table.add_column("Trade")
                table.add_column("Count", justify="right")
                for trade, cnt in trades:
                    table.add_row(trade, str(cnt))
                console.print(table)

            if last:
                console.print("\n[bold]Last Scrape Run[/bold]")
                console.print(f"  Type: {last.run_type}")
                console.print(f"  Month: {last.year_month}")
                console.print(f"  Status: {last.status}")
                console.print(f"  Found: {last.notices_found}")
                console.print(f"  Stored: {last.notices_stored}")
                console.print(f"  Time: {last.created_at}")

    asyncio.run(_status())


@app.command()
def enrich(
    limit: int = typer.Option(50, help="Max procurements to enrich per run"),
):
    """Enrich active procurements with contact info from RHR API."""
    from hanke_radar.scraper.html_enricher import enrich_active_procurements

    console.print(f"[bold]Enriching up to {limit} procurements...[/bold]")
    summary = asyncio.run(enrich_active_procurements(limit=limit))

    table = Table(title="Enrichment Summary")
    table.add_column("Metric")
    table.add_column("Count", justify="right")
    table.add_row("Total checked", str(summary["total"]))
    table.add_row("Enriched", str(summary["enriched"]))
    table.add_row("Skipped", str(summary["skipped"]))
    table.add_row("Errors", str(summary["errors"]))
    table.add_row("Duration", f"{summary['duration_ms']}ms")
    console.print(table)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to listen on"),
):
    """Start the FastAPI REST API server."""
    import uvicorn

    uvicorn.run("hanke_radar.api.app:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    app()
