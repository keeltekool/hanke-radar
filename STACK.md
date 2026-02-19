# HankeRadar — Stack & Architecture Reference

> Last updated: 2026-02-19

---

## Services

| Service | Purpose | Dashboard |
|---------|---------|-----------|
| **Neon PostgreSQL** | Procurement database | [console.neon.tech](https://console.neon.tech) |
| **riigihanked.riik.ee** | Public procurement data source | [riigihanked.riik.ee](https://riigihanked.riik.ee) |
| **GitHub Actions** | Daily automated scraping cron | [Actions tab](https://github.com/keeltekool/hanke-radar/actions) |
| **Render** | REST API hosting (free tier) | TBD — deploy pending |

---

## URLs

| Environment | URL |
|------------|-----|
| API (production) | TBD (Render) |
| API (local) | http://localhost:8000 |
| Swagger docs (local) | http://localhost:8000/docs |
| GitHub | https://github.com/keeltekool/hanke-radar |

---

## Env Vars

| Variable | Where | Description |
|----------|-------|-------------|
| `DATABASE_URL` | `.env.local`, Render, GitHub Secrets | Neon PostgreSQL connection string |

---

## Architecture

```
riigihanked.riik.ee (bulk XML)
        │
        ▼
┌─────────────────────────┐
│  HankeRadar (Python)    │
│                         │
│  [Scraper + Enricher]   │  ← GitHub Actions cron (daily 06:00 UTC)
│  - Bulk XML monthly     │
│  - RHR JSON API enrich  │
│                         │
│  [FastAPI REST API]     │  ← Render (Docker)
│  - GET /procurements    │
│  - GET /trades          │
│  - GET /procurements/stats │
│                         │
│  [Neon PostgreSQL]      │
│  - procurements (421+)  │
│  - scrape_runs          │
│  - trade_cpv_mappings   │
└─────────────┬───────────┘
              │ REST API (CORS)
              ▼
        ┌──────────┐
        │ QuoteKit │  (M3 — next)
        │ (Next.js)│
        └──────────┘
```

---

## Project Structure

```
hanke-radar/
├── hanke_radar/
│   ├── api/
│   │   ├── app.py          # FastAPI app + CORS
│   │   └── routes.py       # All API endpoints
│   ├── cli/
│   │   └── main.py         # Typer CLI: scrape, enrich, expire, status, serve
│   ├── db/
│   │   ├── engine.py       # Async SQLAlchemy + Neon URL conversion
│   │   ├── models.py       # Procurement, ScrapeRun, TradeCpvMapping
│   │   └── seed.py         # CPV → trade mapping seeds
│   ├── scraper/
│   │   ├── bulk_scraper.py # Monthly XML download + parse + upsert
│   │   ├── cpv_filter.py   # CPV prefix matching for trade relevance
│   │   ├── html_enricher.py # RHR JSON API enrichment (contact, address)
│   │   └── xml_parser.py   # eForms UBL XML parser
│   └── config.py           # pydantic-settings env config
├── tests/                  # pytest (25 tests)
├── .github/workflows/
│   └── scrape.yml          # Daily cron: scrape → enrich → expire
├── Dockerfile              # Docker build for Render
├── render.yaml             # Render blueprint
├── pyproject.toml          # uv/Python project config
└── .env.local              # Local env vars (gitignored)
```

---

## DB Schema

### procurements
- `id` SERIAL PK
- `notice_id` TEXT UNIQUE — eForms UUID
- `procurement_id` TEXT — ContractFolderID UUID
- `rhr_id` TEXT — Internal RHR integer ID (for API enrichment)
- `title`, `description` TEXT
- `contracting_auth`, `contracting_auth_reg` TEXT
- `contract_type` TEXT — ehitustööd / teenused / tarned
- `procedure_type` TEXT — Avatud / Lihthange / etc.
- `cpv_primary` TEXT, `cpv_additional` TEXT[]
- `estimated_value` DECIMAL(12,2)
- `nuts_code`, `nuts_name` TEXT — region
- `submission_deadline`, `publication_date` TIMESTAMPTZ
- `status` TEXT — active / expired / awarded
- `source_url` TEXT — link to riigihanked.riik.ee
- `trade_tags` TEXT[] — derived: plumbing, electrical, painting, hvac, general, maintenance
- `contact_person`, `contact_email`, `contact_phone`, `performance_address` TEXT — enrichment
- `enriched_at` TIMESTAMPTZ
- Indexes: cpv, status, deadline, trade_tags (GIN)

### scrape_runs
- Tracks each scrape/enrich job: type, counts, duration, status

### trade_cpv_mappings
- CPV prefix → trade key mapping (seeded on first scrape)

---

## API Endpoints

```
GET  /health                    → {"status": "ok"}
GET  /procurements              → paginated list with filters
       ?trade=plumbing          → filter by trade tag
       ?cpv=45330000            → filter by CPV prefix
       ?region=EE001            → filter by NUTS region
       ?status=active           → active / expired / awarded
       ?min_value=10000         → min estimated value EUR
       ?max_value=100000        → max estimated value EUR
       ?page=1&per_page=20      → pagination
GET  /procurements/stats        → counts by trade, region, status
GET  /procurements/{id}         → single procurement detail
GET  /trades                    → trade categories with counts
GET  /scrape/status             → last 5 scrape runs
```

---

## CLI Commands

```bash
uv run hanke scrape              # Scrape current month XML
uv run hanke scrape --backfill 3 # Scrape last 3 months
uv run hanke enrich --limit 100  # Enrich from RHR JSON API
uv run hanke expire              # Mark past-deadline as expired
uv run hanke status              # Show DB stats
uv run hanke serve               # Start FastAPI server
```

---

## Gotchas

- **asyncpg + Neon:** asyncpg doesn't accept `sslmode` or `channel_binding` as URL params. `engine.py` strips them and passes `ssl=True` via `connect_args`.
- **Route ordering:** `/procurements/stats` MUST be registered before `/procurements/{id}` or FastAPI treats "stats" as an int parameter.
- **RHR API IDs:** The eForms XML uses UUIDs, but the RHR JSON API uses internal integer IDs. We extract `rhr_id` from `CallForTendersDocumentReference` URIs in the XML.
- **Bulk XML size:** Monthly dumps are ~30-36 MB. 120s timeout needed.
- **Enrichment rate:** ~1.3s per procurement (rate limited). 100 procurements ≈ 2 min.

---

## Tech Stack

| Component | Library/Tool | Version |
|-----------|-------------|---------|
| Language | Python | 3.13 |
| Package manager | uv | 0.9.x |
| Web framework | FastAPI | 0.129+ |
| HTTP client | httpx | 0.28+ |
| XML parser | lxml | 6.0+ |
| HTML parser | BeautifulSoup4 | 4.14+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| DB driver | asyncpg | 0.31+ |
| CLI | Typer + Rich | latest |
| Config | pydantic-settings | 2.13+ |
| Linting | ruff | 0.15+ |
| Testing | pytest + pytest-asyncio | latest |
