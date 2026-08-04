# MAINTENANCE

## Issue-driven maintenance

Before any work, check open issues and fix them:

```bash
gh issue list --repo ale23yfm/evolution-gaming-ro-python-scraper --state open
```

Prioritize `critical` → `bug` → `enhancement` → `documentation`. For each
open issue: read it, investigate the root cause, apply the fix, run the
relevant tests, commit with the issue reference (e.g. `fix: resolve #20`),
push, then close the issue with a comment linking the commit.

If an issue cannot be resolved (external API down, board unreachable), add
a comment explaining the blocker, label it `wontfix`/`question` as
appropriate, and move on.

## Routine

- The scheduled `job-seeker-ro-spider.yml` workflow scrapes daily.
- If the scrape fails, check: board reachability, ANAF API status, API response.
- Validate job URLs periodically:

```bash
python3 -m scraper.validate_jobs 36034853 --mode content --dry-run
python3 -m scraper.validate_jobs 36034853 --mode content --delete
```

## Board structure changes

If `parse_api_jobs` returns 0 or few jobs, inspect the board API:

```bash
curl -s "https://careers.evolution.com/wp-json/wp/v2/vacancies"
```

Update the parser fields in `scraper/index.py` (vacancy `id`/`name`/`location`)
and the expected count in `tests/e2e/test_scraper.py`.

## Company data changes

Edit `scraper/config/company.json` only. Run the scraper to regenerate
`docs/company.json`.

## ANAF outages

`get_company_from_anaf` falls back demoanaf.ro → cuiscan.ro → cache
(`scraper/anaf_cache.json`). If all fail, the scraper errors clearly.
