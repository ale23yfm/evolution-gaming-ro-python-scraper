# Contributing

## Getting started

```bash
git clone git@github.com:ale23yfm/evolution-gaming-ro-python-scraper.git
cd evolution-gaming-ro-python-scraper
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Reporting issues

Every code change must have a corresponding GitHub issue — see
[`ai/ISSUES.md`](ai/ISSUES.md). Open issues at
[ale23yfm/evolution-gaming-ro-python-scraper/issues](https://github.com/ale23yfm/evolution-gaming-ro-python-scraper/issues).

### Bug report structure

Bug reports must follow this structure:

- **ENVIRONMENT** — OS, Python version, and the command / configuration used.
- **STEPS TO REPRODUCE** — numbered steps that trigger the bug.
- **EXPECTED RESULTS** — what should happen.
- **ACTUAL RESULTS** — what actually happens (include error messages and logs).

Use this template:

```markdown
### ENVIRONMENT
- OS: ...
- Python: ...
- Command / config: ...

### STEPS TO REPRODUCE
1. ...
2. ...
3. ...

### EXPECTED RESULTS
...

### ACTUAL RESULTS
...
```

## Code style

- Python 3.9+.
- No comments unless they explain *why* (mirrors repo conventions).
- Module-level docstrings; short function docstrings.
- Run tests before pushing:

```bash
python3 -m pytest tests/unit tests/consistency
```

## Adding a test

Add to the appropriate directory under `tests/`:

- `unit/` — mocked HTTP, no network.
- `integration/` — live APIs, `pytest.skip` when unreachable.
- `e2e/` — real board scrape, `pytest.skip` when unreachable.
- `consistency/` — repo identity and template conventions.

## Updating company data

Only edit `scraper/config/company.json` (single source of truth). After a
scrape, `docs/company.json` is regenerated automatically.
