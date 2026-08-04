# Instructions

## Project Purpose

This scraper extracts job listings for **EVOLUTION PRODUCTS RO S.R.L.** (CIF `36034853`)
from the careers.evolution.com board, filtered to Romania (`location.country == "ro"`),
and publishes them to peviitor.ro via the v1 API (`https://api.peviitor.ro/v1`).

Target: `https://careers.evolution.com/wp-json/wp/v2/vacancies`

## Model Schemas

The job and company models are defined in:
- `ai/JOB_MODEL.md` — job model schema
- `ai/COMPANY_MODEL.md` — company model schema

## Important

These models are **dynamic** and can change over time. They are based on
the official Peviitor Core schemas which may be updated.

## How to Keep Models Updated

When working on this scraper:

1. **Check for updates** in the Peviitor Core repository:
   - Repository: https://github.com/peviitor-ro/peviitor_core
   - Main file: README.md (contains Job and Company model schemas)

2. **When to update**:
   - Before starting new development work
   - If field requirements or validations have changed
   - If new fields have been added

3. **How to update**:
   - Fetch the latest README.md from peviitor_core main branch
   - Compare with current `ai/JOB_MODEL.md` and `ai/COMPANY_MODEL.md`
   - Update local files if there are differences
   - Update `scraper/index.py` mapping logic if field requirements changed

## Technologies

- **Python 3.12** — scraping and data extraction (`requests`, `bs4`)
- **Peviitor v1 API** — data storage and retrieval (`api.peviitor.ro/v1`)
- **pytest** — unit / integration / e2e / consistency tests

## Workflow Steps

1. **Start with brand** — `EVOLUTION`
2. **Search in ANAF/CUIScan** — find company by CIF `36034853`
3. **Get company details from ANAF** — fetch full company data via CUIScan → demoanaf → cache
4. **Validate with Peviitor** — verify company exists in peviitor
5. **Check existing jobs** — query peviitor v1 API by CIF to see what jobs exist
6. **Check company status** — if ANAF status = INACTIVE → DELETE existing jobs and STOP
7. **Scrape new jobs** — parse the careers.evolution.com board (Romania filter)
8. **Transform for API** — validate and fix job data:
   - location: only Romanian cities allowed (fallback `["România"]`)
   - workmode: `remote` / `on-site` / `hybrid`
   - company: uppercase
9. **Upsert to API** — import/update jobs via peviitor v1 API
10. **Verify URLs** — check existing job URLs still work, delete stale board URLs

## Running the Scraper

```bash
# Run the full scraper workflow (single command)
python3 -m scraper.index
```

> **Important**: The scraper does NOT delete jobs from other sources
> (ANOFM, jobviewtrack, ejobs, olx, multijobs, targuldecariere). Stale
> deletion is scoped to the careers.evolution.com board URL prefix only, so jobs
> published by other scrapers under the shared CIF are preserved.

## Full Workflow (automatic)

When running `python3 -m scraper.index`, the following steps happen automatically:

1. **Check existing jobs count** — query peviitor v1 API by CIF (read-only)
2. **Validate company via ANAF** — check company exists and is active
3. **Upsert company core** — with `scraperFile` pointing to our workflow
4. **Scrape jobs** — parse the careers.evolution.com board
5. **Merge ANOFM jobs** — unless `--test`
6. **Transform for API** — fix locations (only Romanian cities), normalize workmode
7. **Generate files** — `scraper/jobs.json`, `docs/jobs.md`, `docs/company.json`
8. **Upsert to API** — add/update jobs (API handles duplicates by URL)
9. **Delete stale jobs** — remove careers.evolution.com-board jobs no longer on the site
10. **Show Summary** — log job counts

## Workflow Flowchart

```
scraper/config/company.json (single source of truth: CIF, brand, URLs)
    │
    ▼
scraper/index.py
    │
    ▼
query_solr(CIF) - check existing jobs (peviitor v1 API)
    │
    ▼
company.py / anaf.py (validate company)
    ├── CUIScan ──► get company name + CIF
    ├── demoanaf ─► fallback
    ├── anaf_cache.json ──► fallback if APIs fail
    │
    ▼ (if active)
scrape careers.evolution.com board (Romania filter)
    │
    ▼
transform_jobs_for_solr()
    ├── Filter: keep only Romanian locations
    ├── Fallback: "România" for unknown
    └── Normalize: workmode, uppercase company
    │
    ▼
upsert_jobs() - API handles duplicate by URL
    │
    ▼
delete stale careers.evolution.com-board URLs
    │
    ▼
generate_jobs_markdown() → docs/jobs.md
    └── committed to repo by CI
```

## File Responsibilities

See `ai/files.md` for the full file map. Key files:

| File | Role |
|------|------|
| `scraper/config/company.json` | **Single source of truth** for company identity (CIF, brand, URLs, `scraperFile`) |
| `scraper/config/scraper.json` | Board config — `apiBase`, `apiPath`, `jobDetailsPrefix` |
| `scraper/index.py` | Main entry point — validate company → scrape → transform → upsert → delete stale → generate `docs/jobs.md` |
| `scraper/api.py` | Peviitor v1 API client — query/upsert/delete jobs + company |
| `scraper/anaf.py` | Company validation — CUIScan + demoanaf + cache fallback |
| `scraper/job_validator.py` | Shared URL validation primitives (head/content/browser) |
| `scraper/validate_jobs.py` | CLI deep validator (`--mode head|content|browser`, `--delete`) |
| `scraper/markdown_generator.py` | Generates `docs/jobs.md` |
| `tests/unit/*` | Unit tests for index/api/anaf/config/job_validator |
| `tests/integration/test_company_real.py` | Live integration — ANAF + peviitor API |
| `tests/e2e/test_scraper.py` | E2E — real careers.evolution.com board scrape |
| `tests/consistency/test_repo.py` | Repo identity, root files, workflow naming |

## API Endpoints

- **EVOLUTION board**: `https://careers.evolution.com/wp-json/wp/v2/vacancies` — JSON API (Romania filter)
- **ANOFM search**: `https://mediere.anofm.ro/api/entity/vw_public_job_posting` — POST by `employer_tax_code`
- **CUIScan**: `https://cuiscan.ro/api.php?action=company&cui=CIF` — company details fallback
- **DemoANAF**: `https://demoanaf.ro/api/company/:cui` — company details fallback
- **CUIFirma search**: `https://www.cuifirma.ro/api/search?q=BRAND` — search fallback
- **Peviitor v1 API**: `https://api.peviitor.ro/v1/` — all job and company operations go through this API (no direct Solr)

## Rate Limiting & Politeness

The scraper is intentionally slow to be a good citizen:

| Setting | Value | Where |
|---------|-------|-------|
| Request timeout | 10 s | `scraper/api.py`, `scraper/anaf.py` — `TIMEOUT` |
| ANAF fallback | 1 attempt CUIScan → demoanaf → cache | `scraper/anaf.py` — no retries, just fallback |
| Concurrency | 1 (sequential) | No parallel fetches |
| User-Agent | `job_seeker_ro_spider` | Identifies the scraper in server logs |
| Extra requests | Only per-job HEAD/content checks during validation | `scraper/validate_jobs.py` |

Respect `robots.txt` when present; do not crawl aggressively.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_REPOSITORY` | Used by consistency tests — format `owner/repo` |
| `GITHUB_TOKEN` | GitHub API token for consistency tests |

Never commit secrets or `.env` files.

## Standalone Commands

```bash
# Full scrape + publish (also --test to skip ANOFM merge)
python3 -m scraper.index
python3 -m scraper.index --test

# Query jobs in peviitor by CIF (read-only verify; add --delete to remove
# invalid board URLs — deletion is scoped to the careers.evolution.com board prefix,
# so jobs from other scrapers under a shared CIF are never touched)
python3 -m scraper.api 36034853

# Validate job URLs from peviitor by CIF (head/content/browser)
python3 -m scraper.validate_jobs 36034853 --mode head
python3 -m scraper.validate_jobs 36034853 --mode content --dry-run
python3 -m scraper.validate_jobs 36034853 --mode content --delete
```

## Testing

This project requires multiple levels of testing:

1. **Unit Tests** — individual modules in isolation (`tests/unit`)
2. **Integration Tests** — live APIs, skip-safe (`tests/integration`)
3. **E2E Tests** — full pipeline against the real board, skip-safe (`tests/e2e`)
4. **Consistency Tests** — repo identity and conventions (`tests/consistency`)

Run tests:

```bash
python3 -m pytest tests/unit tests/consistency   # offline
python3 -m pytest tests/integration              # live APIs (skip-safe)
python3 -m pytest tests/e2e                      # real board (skip-safe)
python3 -m pytest                                # everything
```

## Temporary Files

All temporary/scratch files go in `tmp/` inside the project root — never
outside the project. `tmp/` is in `.gitignore` and will not be committed.

## GitHub Actions

- `job-seeker-ro-spider.yml` — scheduled scrape (cron) + manual dispatch.
- `automation-testing.yml` — runs unit/consistency tests on every push.
- `job-deep-validate.yml` — deep job-URL validation on demand.
- `job-recovery-from-disaster.yml` — rebuild from backup on demand.
- `automation-template-sync-check.yml` — weekly template-sync check.
