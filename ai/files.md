# Project Files

## Python Files — scraper/

| File | Description |
|------|-------------|
| `scraper/index.py` | Main scraper - full workflow: validate company (ANAF) → scrape careers.evolution.com board → merge ANOFM → transform → upsert to peviitor v1 API → delete stale → generate `docs/jobs.md`. Entry point: `python3 -m scraper.index` |
| `scraper/api.py` | Peviitor v1 API client - `query_solr`, `upsert_company`, `upsert_jobs`, `delete_jobs_by_cif`, `delete_job_by_url` |
| `scraper/anaf.py` | Multi-source company data module - CUIScan + demoanaf (details), demoanaf + cuifirma (search), ANAF cache fallback (`scraper/anaf_cache.json`) |
| `scraper/job_validator.py` | Shared validation primitives - `validate_by_head`, `validate_by_content`, `validate_by_browser`, `DEFAULT_EXPIRED_KEYWORDS`. Content check strips `<script>`/`<style>` |
| `scraper/validate_jobs.py` | CLI job URL validator (`--mode head|content|browser`, `--dry-run`, `--delete`). Entry point: `python3 -m scraper.validate_jobs` |
| `scraper/markdown_generator.py` | Generates `docs/jobs.md` and `docs/company.json` |
| `scraper/company.py` | Thin wrapper that loads `scraper/config/company.json` |

## Config — scraper/config/

| File | Description |
|------|-------------|
| `scraper/config/company.json` | **Single source of truth for company identity** (`id`, `company`, `brand`, `location`, `website`, `career`, `scraperFile`). `scraperFile` must be the GitHub Actions workflow URL |
| `scraper/config/scraper.json` | Board-specific config - `apiBase`, `apiPath`, `jobDetailsPrefix` |

## Test Files — tests/

| File | Description |
|------|-------------|
| `tests/conftest.py` | Fixtures: config loaders, mocked API responses, lowered timeouts |
| `tests/unit/test_index.py` | Unit tests - `parse_api_jobs`, `map_to_job_model`, `transform_jobs_for_solr`, location/workmode normalization |
| `tests/unit/test_api.py` | Unit tests - query/upsert/delete, HTTP error handling |
| `tests/unit/test_anaf.py` | Unit tests - ANAF/CUIScan fetch and fallback caching |
| `tests/unit/test_config.py` | Unit tests - company/scraper config shape |
| `tests/unit/test_job_validator.py` | Unit tests - head/content/browser validation |
| `tests/integration/test_company_real.py` | Live integration - ANAF + peviitor API (skip-safe) |
| `tests/e2e/test_scraper.py` | E2E - real careers.evolution.com board scrape (skip-safe) |
| `tests/consistency/test_repo.py` | Verifies repo is public, has the workflows, and required topics |

## Markdown Files — ai/

| File | Description |
|------|-------------|
| `ai/AGENTS.md` | Rules for AI agents working on this project |
| `ai/BRANCH.md` | Branch strategy |
| `ai/INSTRUCTIONS.md` | How to run the scraper, validate URLs, run tests |
| `ai/ISSUES.md` | Issue tracking rule (issue for every code change) + triage |
| `ai/JOB_MODEL.md` | Job schema definition (peviitor) |
| `ai/COMPANY_MODEL.md` | Company schema definition (peviitor) |
| `ai/MAINTENANCE.md` | Issue-driven maintenance workflow |
| `ai/PUBLIC.md` | Public repo URLs |
| `ai/ROBOTS.md` | Scraping policy and polite-crawl rules |
| `ai/TOPICS.md` | Applied GitHub topics |
| `ai/UPDATE-REPO-ABOUT.md` | Repo description/website maintenance |
| `ai/VERIFY.md` | Step-by-step verification checklist |
| `ai/files.md` | This file - documents the role of each project file |

## Configuration / Infrastructure Files

| File | Description |
|------|-------------|
| `requirements.txt` | Python dependencies (requests, bs4, pytest) |
| `pytest.ini` | Pytest configuration |
| `.gitignore` | Ignores `.venv/`, `__pycache__/`, `scraper/jobs.json`, `scraper/anaf_cache.json`, `tmp/` |
| `CHANGELOG.md` | Version history and notable changes |
| `CONTRIBUTING.md` | Contribution guidelines |
| `SECURITY.md` | Security policy and vulnerability reporting |
| `.github/workflows/job-seeker-ro-spider.yml` | Daily scraping workflow (scheduled + dispatch) |
| `.github/workflows/automation-testing.yml` | Runs unit/consistency tests on every push |
| `.github/workflows/job-deep-validate.yml` | Manual deep job-URL validation |
| `.github/workflows/job-recovery-from-disaster.yml` | Rebuild from backup on demand |
| `.github/workflows/automation-template-sync-check.yml` | Weekly template-sync check |

## Data Files

| File | Description |
|------|-------------|
| `scraper/jobs.json` | Scraped jobs cache (gitignored) |
| `scraper/anaf_cache.json` | ANAF company cache (gitignored) |
| `docs/jobs.md` | Scraped jobs in markdown (regenerated on each scrape, served on GitHub Pages) |
| `docs/company.json` | Static copy of `scraper/config/company.json` (regenerated) |
| `docs/index.html` | GitHub Pages site root (served from `docs/` on `main`, built automatically) |

## Notes

- All operations go through the peviitor v1 API — no direct Solr access.
- CIF `36034853` is shared with other peviitor scrapers; stale-deletion is
  scoped to the careers.evolution.com board prefix only.
- Full workflow: validate company (ANAF) → scrape EVOLUTION board → merge
  ANOFM → transform → upsert → delete stale → generate `docs/jobs.md`.
