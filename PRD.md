# HankeRadar — PRD

> Estonian Public Procurement Scraper & Feed Service
> Last updated: 2026-02-18

---

## Problem

Estonian tradespeople (plumbers, electricians, painters, HVAC technicians) miss public sector work opportunities because:

1. **The register is hard to use** — riigihanked.riik.ee is a React SPA designed for procurement officers, not tradespeople
2. **No filtering by trade** — you can't subscribe to "plumbing jobs in Tallinn"
3. **No integration with their tools** — finding a tender and creating a quote are completely separate workflows
4. **Information overload** — large enterprise IT tenders mixed with small building maintenance jobs

QuoteKit already knows each user's trade, service catalog, and pricing. If we feed procurement data into QuoteKit, tradespeople get **actionable leads with one-click quote creation**.

---

## Solution

**HankeRadar** is a standalone Python service that:

1. Scrapes Estonia's public procurement register (riigihanked.riik.ee)
2. Parses, filters, and stores trade-relevant procurements
3. Exposes a REST API that any app can consume
4. Integrates first with QuoteKit as a "Hanked" (Procurements) feed

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   HankeRadar (Python)                │
│                                                      │
│  [Scraper]                    [FastAPI REST API]     │
│  - Bulk XML monthly dumps     - GET /procurements    │
│  - Individual notice HTML     - GET /procurements/id │
│  - Scheduled via GH Actions   - Filter by CPV/region │
│                                                      │
│  [Neon PostgreSQL]                                   │
│  - procurements table                                │
│  - scrape_runs table (state tracking)                │
│                                                      │
└──────────────┬──────────────────┬────────────────────┘
               │ API              │ API (future)
               ▼                  ▼
         ┌──────────┐      ┌──────────────┐
         │ QuoteKit │      │ Lead Radar   │
         │ (Next.js)│      │ (Next.js)    │
         └──────────┘      └──────────────┘
```

### Why separate repo, not inside QuoteKit

- **Reusability** — Lead Radar, future projects can consume the same API
- **Runtime isolation** — Python + Next.js in one repo = deployment nightmare
- **Independent deploy cycle** — scraper schedule != frontend deploys
- **Follows existing pattern** — same as city24-proxy CF Worker (isolated service, multiple consumers)

### Deployment

| Component | Platform | Cost |
|-----------|----------|------|
| Scraper (cron) | GitHub Actions (scheduled workflow) | Free (2000 min/month private repo) |
| REST API | Railway or Render | Free tier (500-750 hrs/month) |
| Database | Neon PostgreSQL | Free tier (shared with existing projects) |

---

## Data Source — Confirmed Technical Findings

### What riigihanked.riik.ee exposes (verified 2026-02-18)

**Working endpoints (unauthenticated):**

| Endpoint | Format | Use |
|----------|--------|-----|
| `GET /rhr/api/public/v1/opendata/notice/{year}/month/{month}/xml` | XML | Bulk monthly dump — primary data source |
| `GET /rhr/api/public/v1/notice/{noticeId}/html` | HTML | Individual notice detail — enrichment source |

**Not available:**

- No public search/filter API (frontend uses internal session-based POST calls)
- No JSON endpoints
- No Swagger/OpenAPI docs
- No RSS feeds
- No documented rate limits (but no explicit ToS either)

### Procurement threshold reality

Only procurements **above these values** appear in the register:

| Type | Minimum Value (must publish) |
|------|------------------------------|
| Services / Goods | >= EUR 30,000 |
| Construction work | >= EUR 60,000 |

Below these thresholds, agencies handle procurement internally — that data simply does not exist publicly.

**This is still valuable.** EUR 60k+ construction jobs are exactly what a small plumbing company, electrical contractor, or painting crew bids on: school renovations, office refits, building maintenance contracts.

### Procurement types in the register

| Estonian | English | Relevance |
|----------|---------|-----------|
| Lihthankemenetlus / Lihthange | Simplified procedure | **Most relevant** — smaller jobs, less bureaucracy |
| Avatud hankemenetlus | Open procedure | Above national threshold, open to all |
| Piiratud hankemenetlus | Restricted procedure | Pre-qualification required |
| Raamleping | Framework agreement | Ongoing service contracts |

**Primary filter:** Lihthange + Avatud for construction/maintenance CPV codes.

---

## CPV Codes — Confirmed from Real Notices

### Plumbing (Torustik / Sanitaar)

| CPV | Estonian | English |
|-----|----------|---------|
| 45330000 | Torustiku- ja sanitaartööd | Plumbing and sanitary works |
| 45332000 | Veevarustus- ja kanalisatsioonitööd | Water supply and drainage |
| 45332200 | Veevärgi paigaldustööd | Water-pipeline installation |
| 45332400 | Sanitaartehnika paigaldustööd | Sanitary fittings installation |

### Electrical (Elekter)

| CPV | Estonian | English |
|-----|----------|---------|
| 45310000 | Elektripaigaldustööd | Electrical installation work |
| 45311000 | Elektrijuhtimis- ja kaabeltööd | Electrical wiring and fitting |
| 45315000 | Elektri soojendussüsteemi töö | Electrical heating installation |
| 45317000 | Muu elektriseadmete paigaldustöö | Other electrical installation |

### Painting (Värvimine / Maalimine)

| CPV | Estonian | English |
|-----|----------|---------|
| 45440000 | Maali- ja klaasimistööd | Painting and glazing work |
| 45442000 | Pindade katmistööd | Protective coatings |
| 45442100 | Ehitiste värvimistööd | Building painting |

### HVAC (Küte / Ventilatsioon)

| CPV | Estonian | English |
|-----|----------|---------|
| 45331000 | Katelde, torude paigaldustööd | Boiler and pipe installation |
| 45331100 | Keskkütte paigaldustööd | Central heating installation |
| 45331200 | Ventilatsiooni- ja kliimaseadmete paigaldustööd | HVAC installation |
| 45331210 | Ventilatsiooniseadmete paigaldustööd | Ventilation equipment installation |

### General Construction / Maintenance

| CPV | Estonian | English |
|-----|----------|---------|
| 45000000 | Ehitustööd | Construction work (parent) |
| 45210000 | Hoonete ehitustöö | Building construction |
| 45400000 | Hoone viimistlustööd | Building completion/finishing |
| 45430000 | Põranda- ja seinakatte paigaldustööd | Flooring and wall covering |
| 45450000 | Muu hoone viimistlustöö | Other building completion |
| 50700000 | Hoonete seadmete remondi- ja hooldusteenused | Building equipment maintenance |
| 50710000 | Elektri- ja mehaaniliste seadmete remondi- ja hooldusteenused | Electrical/mechanical maintenance |

---

## Data Model

### `procurements` table

```sql
CREATE TABLE procurements (
  id                  SERIAL PRIMARY KEY,
  notice_id           TEXT NOT NULL UNIQUE,       -- riigihanked notice ID
  procurement_id      TEXT,                        -- internal procurement ID (sisemine tunnus)
  title               TEXT NOT NULL,               -- pealkiri
  description         TEXT,                        -- kirjeldus
  contracting_auth    TEXT NOT NULL,               -- hankija nimi
  contracting_auth_reg TEXT,                       -- registreerimisnumber
  contract_type       TEXT,                        -- ehitustööd / teenused / tarned
  procedure_type      TEXT,                        -- lihthange / avatud / etc.
  cpv_primary         TEXT,                        -- primary CPV code
  cpv_additional      TEXT[],                      -- additional CPV codes
  estimated_value     DECIMAL(12,2),               -- eeldatav maksumus (EUR, excl. VAT)
  nuts_code           TEXT,                        -- NUTS region (EE001, EE009, etc.)
  nuts_name           TEXT,                        -- region name (Põhja-Eesti, etc.)
  submission_deadline TIMESTAMPTZ,                 -- pakkumuste esitamise tähtaeg
  publication_date    TIMESTAMPTZ,                 -- teate saatmise kuupäev
  duration_months     INTEGER,                     -- kestus (kuudes)
  start_date          DATE,                        -- alguskuupäev
  status              TEXT DEFAULT 'active',        -- active / expired / awarded
  source_url          TEXT,                        -- link to notice on riigihanked
  raw_html            TEXT,                        -- cached notice HTML (for re-parsing)
  trade_tags          TEXT[],                      -- derived: ['plumbing', 'electrical', etc.]
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_procurements_cpv ON procurements (cpv_primary);
CREATE INDEX idx_procurements_status ON procurements (status);
CREATE INDEX idx_procurements_deadline ON procurements (submission_deadline);
CREATE INDEX idx_procurements_trade ON procurements USING GIN (trade_tags);
```

### `scrape_runs` table (operational tracking)

```sql
CREATE TABLE scrape_runs (
  id              SERIAL PRIMARY KEY,
  run_type        TEXT NOT NULL,          -- 'bulk_xml' / 'notice_html' / 'status_update'
  year_month      TEXT,                   -- '2026-02' (for bulk runs)
  notices_found   INTEGER DEFAULT 0,
  notices_stored  INTEGER DEFAULT 0,
  notices_skipped INTEGER DEFAULT 0,
  errors          INTEGER DEFAULT 0,
  duration_ms     INTEGER,
  status          TEXT DEFAULT 'running', -- running / completed / failed
  error_message   TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### `trade_cpv_mappings` table (configurable CPV → trade mapping)

```sql
CREATE TABLE trade_cpv_mappings (
  id          SERIAL PRIMARY KEY,
  cpv_prefix  TEXT NOT NULL,            -- e.g., '4533' matches 45330000, 45332000, etc.
  trade_key   TEXT NOT NULL,            -- 'plumbing', 'electrical', 'painting', 'hvac', 'general'
  trade_name_et TEXT NOT NULL,          -- 'Torustik', 'Elekter', etc.
  trade_name_en TEXT NOT NULL           -- 'Plumbing', 'Electrical', etc.
);
```

---

## Python Tech Stack

| Component | Library | Why |
|-----------|---------|-----|
| Web framework | **FastAPI** | Async, auto-docs (Swagger), type hints, industry standard |
| HTTP client | **httpx** | Async HTTP, modern Python requests replacement |
| XML parsing | **lxml** | Fast XML/HTML parser, XPath support |
| HTML parsing | **BeautifulSoup4** | Fallback for notice HTML parsing |
| Database | **asyncpg** + **SQLAlchemy** (async) | Direct Neon PostgreSQL, async for performance |
| Migrations | **Alembic** | DB schema versioning |
| Scheduling | **GitHub Actions cron** | Free, no infra, runs daily |
| Task runner | **Typer** (CLI) | CLI commands: `hanke scrape`, `hanke status`, etc. |
| Config | **pydantic-settings** | Env var management with validation |
| Testing | **pytest** + **pytest-asyncio** | Standard Python testing |
| Linting | **ruff** | Fast Python linter + formatter (replaces black, isort, flake8) |

### Python version: 3.12+

---

## API Endpoints (FastAPI)

```
GET  /health                          -- service health check
GET  /procurements                    -- list procurements (paginated)
       ?trade=plumbing                -- filter by trade tag
       ?cpv=45330000                  -- filter by CPV code
       ?region=EE001                  -- filter by NUTS region
       ?status=active                 -- filter by status
       ?min_value=10000               -- min estimated value EUR
       ?max_value=100000              -- max estimated value EUR
       ?page=1&per_page=20            -- pagination
GET  /procurements/{id}               -- single procurement detail
GET  /procurements/stats              -- counts by trade, region, status
GET  /trades                          -- list available trade categories
GET  /scrape/status                   -- last scrape run info
POST /scrape/trigger                  -- manually trigger scrape (auth required)
```

All endpoints return JSON. CORS enabled for QuoteKit + Lead Radar origins.

---

## Scraping Strategy

### Phase 1: Bulk XML ingestion (primary)

```python
# Monthly bulk dump — covers all notices for that month
GET /rhr/api/public/v1/opendata/notice/{year}/month/{month}/xml

# Parse XML → extract procurement fields → filter by CPV code prefix
# Store matching procurements in Neon DB
# Run monthly for backfill, then daily for current month
```

### Phase 2: HTML enrichment (supplementary)

```python
# For procurements that need more detail than XML provides
GET /rhr/api/public/v1/notice/{noticeId}/html

# Parse structured HTML sections:
# Section 1: Hankija (contracting authority details)
# Section 2: Menetlus (procedure, CPV, value, conditions)
# Section 5: Osa/Lot (lot-level details)
# Section 6: Tulemused (results — award notices)
```

### Phase 3: Status monitoring

```python
# Daily job: check if active procurements have passed deadline
# Mark expired procurements as 'expired'
# Check for award notices (results) and update status to 'awarded'
```

### Schedule (GitHub Actions)

```yaml
# .github/workflows/scrape.yml
on:
  schedule:
    - cron: '0 6 * * *'    # Daily at 06:00 UTC (09:00 EET)
  workflow_dispatch:         # Manual trigger
```

---

## QuoteKit Integration (Consumer Side)

### New QuoteKit page: `/dashboard/hanked`

- Lists active procurements matching the user's trade (from business_profiles.trade_type)
- Filter by region (NUTS), value range, deadline
- Sort by deadline (soonest first), value, publication date
- Each procurement card shows: title, contracting authority, deadline, estimated value, region
- **"Create Quote" button** → pre-fills a new quote with:
  - Client: contracting authority name + reg number
  - Title: procurement title
  - Reference: procurement ID / notice ID

### QuoteKit API route: `/api/procurements`

- Proxy to HankeRadar API (or direct DB read if shared Neon)
- Maps user's trade_type to CPV trade tags
- Adds deadline countdown, "new" badges for recent listings

### Trade mapping (QuoteKit → HankeRadar)

| QuoteKit trade_type | HankeRadar trade_tag |
|--------------------|-----------------------|
| plumber | plumbing, hvac |
| electrician | electrical |
| painter | painting |
| general_contractor | general, plumbing, electrical, painting, hvac |
| hvac_technician | hvac |
| renovation | general, painting, flooring |

---

## Milestones

### M1 — Python Scaffold + Bulk XML Scraper (Week 1)

- [ ] Project setup: FastAPI, Poetry/uv, ruff, pytest
- [ ] Neon DB: create tables (procurements, scrape_runs, trade_cpv_mappings)
- [ ] Alembic migrations setup
- [ ] XML parser: download + parse monthly bulk XML
- [ ] CPV filter: keep only trade-relevant procurements
- [ ] Trade tagger: derive trade_tags from CPV codes
- [ ] CLI: `hanke scrape --year 2026 --month 2`
- [ ] Backfill: scrape last 3 months of data
- [ ] GitHub repo + push

**Deliverable:** Running scraper that populates Neon DB with filtered procurements.

### M2 — REST API + Status Monitoring (Week 2)

- [ ] FastAPI endpoints: /procurements, /procurements/{id}, /trades, /stats
- [ ] Pagination, filtering, sorting
- [ ] CORS configuration
- [ ] HTML enrichment parser (individual notice detail)
- [ ] Status monitoring: mark expired/awarded procurements
- [ ] GitHub Actions: daily cron workflow
- [ ] Deploy API to Railway or Render
- [ ] Basic tests

**Deliverable:** Live API returning filtered Estonian procurement data.

### M3 — QuoteKit Integration (Week 3)

- [ ] QuoteKit: new `/dashboard/hanked` page
- [ ] QuoteKit: API proxy route to HankeRadar
- [ ] Trade-based filtering (user's trade → matching procurements)
- [ ] Procurement detail modal/page
- [ ] "Create Quote" flow: procurement → pre-filled quote
- [ ] ET/EN translations for procurement UI
- [ ] Deploy QuoteKit update

**Deliverable:** QuoteKit users see relevant public procurement opportunities and can create quotes from them.

### M4 — Polish + Notifications (Week 4, optional)

- [ ] Email/push notification when new matching procurements appear
- [ ] Deadline reminders (3 days, 1 day before)
- [ ] Procurement statistics dashboard
- [ ] Lead Radar integration (if demand exists)
- [ ] Historical analytics (awarded values by trade/region)

---

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Bulk XML endpoint changes format/URL | Low | Version-pin parser, add format detection, alert on parse failures |
| Bulk XML files are very large (slow download) | Medium | Stream-parse XML (iterparse), don't load full file into memory |
| riigihanked blocks automated access | Low | Respectful rate limiting (1 req/sec), proper User-Agent, daily not hourly |
| XML doesn't contain all needed fields | Medium | Supplement with HTML notice endpoint for missing details |
| Neon free tier storage limits | Low | Only store trade-relevant procurements (not all ~2000+/month), prune expired > 6 months |
| CPV code coverage misses relevant tenders | Medium | Start broad (45xxx parent codes), refine based on real data analysis |
| Threshold reform raises minimums | Low | Monitor legislative changes, update PRD if thresholds change |

---

## Out of Scope (for now)

- Sub-threshold procurements (< EUR 30k/60k) — not in the register
- EU TED cross-border tenders — Estonian register sufficient for local tradespeople
- Automatic bid/tender submission — legal and technical complexity too high
- PDF document parsing (tender documents) — complex, low ROI for MVP
- AI analysis of procurement descriptions — nice-to-have for later

---

## Success Metrics

1. **Data coverage:** >= 90% of trade-relevant procurements captured from register
2. **Data freshness:** New procurements visible in QuoteKit within 24h of publication
3. **User engagement:** QuoteKit users visit Hanked tab >= 2x/week
4. **Quote conversion:** >= 10% of procurement views result in a quote being created
5. **Scraper reliability:** >= 95% daily scrape success rate over 30 days
