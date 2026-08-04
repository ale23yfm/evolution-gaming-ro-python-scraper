# AGENTS.md

Instructions for AI agents working in this repository.

## Project

Python scraper that reads job listings from the EVOLUTION PRODUCTS RO S.R.L.
careers.evolution.com board and publishes them to peviitor.ro through the **v1 API**
(`https://api.peviitor.ro/v1`). It is a Python port of the Node.js EPAM
template and must follow the same API contract.

## Commandments

1. **Never** call Solr directly — use the peviitor v1 API only.
2. Company CIFs are used **as-is** — never zero-pad or transform them.
3. Use `User-Agent: job_seeker_ro_spider`.
4. Edit `scraper/config/company.json` — it is the single source of truth.
5. Run `python3 -m pytest tests/unit tests/consistency` before pushing.
6. Do not add comments unless they explain *why*.
7. Do not commit secrets, `jobs.json`, or the ANAF cache.
8. **Every code change must have a corresponding GitHub issue** (see
   [ISSUES.md](ISSUES.md)) — create the issue before implementing, and
   reference it in the commit message (e.g. `fix: #12 ...`). Exceptions:
   typos, whitespace, and minor documentation.

## Temporary files

All temporary/scratch files go in `tmp/` inside the project root — never
outside the project. `tmp/` is gitignored.

## Background tasks — always pass `--repo` to `gh`

`gh` uses the current directory's git remote by default. When polling a
workflow run (`gh run view ...`) from a different CWD, it returns 404 and
the loop hangs forever. Always pass `--repo` explicitly:

```bash
gh run view <RUN_ID> --repo ale23yfm/evolution-gaming-ro-python-scraper --json status -q .status
```

If a background task is stuck, kill it immediately instead of letting it
hang.

## Commit & push

- `git add -A && git commit -m "..." && git push`
- Commit messages reference the issue they close (e.g. `fix: #12 ...`)
- Never `--force` push

## Do not modify template-derived files

These shared modules are ported from the parent scraper template and must
stay uniform across derived scrapers — do not edit them for company-specific
reasons:

- `scraper/api.py`
- `scraper/anaf.py`
- `scraper/company.py`
- `scraper/job_validator.py`
- `scraper/markdown_generator.py`
- `scraper/validate_jobs.py`

Company-specific logic belongs in `scraper/index.py` and
`scraper/config/*.json`. If a template-wide bug is found in a shared
module, file an issue and sync the fix back to the source template.

## Maintenance

On every session: check open GitHub issues
(`gh issue list --repo ale23yfm/evolution-gaming-ro-python-scraper --state open`),
prioritize `critical` → `bug` → `enhancement` → `documentation`, and fix
them — commit with the issue reference and close the issue.

## Quick commands

```bash
python3 -m pytest tests/unit tests/consistency   # fast tests (no network)
python3 -m pytest tests/e2e                      # real board scrape
python3 -m scraper.index                         # full scrape + publish
python3 -m scraper.validate_jobs 36034853 --mode head  # validate job URLs
```

## Key files

- `scraper/index.py` — entry point and orchestration.
- `scraper/api.py` — peviitor v1 client.
- `scraper/anaf.py` — ANAF + CUIScan company validation.
- `scraper/config/company.json` — company identity/config.
