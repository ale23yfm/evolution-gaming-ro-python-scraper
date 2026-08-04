# VERIFY

How to verify the scraper works.

## Offline

```bash
python3 -m pytest tests/unit tests/consistency
```

Expect: all green, no network needed.

## Live — company

```bash
python3 -c "from scraper.anaf import get_company_from_anaf; print(get_company_from_anaf('36034853'))"
```

Expect: `denumire == "EVOLUTION PRODUCTS RO S.R.L."`, `cif == "36034853"`.

## Live — board

```bash
python3 -m pytest tests/e2e
```

Expect: `>= 1` jobs scraped, unique URLs, titles present, Romania filter applied.

## Live — peviitor SOLR

```bash
curl "https://api.peviitor.ro/v1/scraper/jobs/?cif=36034853&rows=500"
```

Expect: `success: true`. Note CIF `36034853` is shared with other peviitor
scrapers (jobviewtrack, ejobs, olx, multijobs, targuldecariere), so the
total count includes their jobs; confirm the scraped careers.evolution.com URLs
are present.

## Full pipeline

```bash
python3 -m scraper.index
```

Then check:

- `scraper/jobs.json` exists and has jobs.
- `docs/jobs.md` regenerated with the job list.
- `docs/company.json` mirrors `scraper/config/company.json`.
- SOLR count matches scraped count (minus filtered locations).

## GitHub Pages

```bash
gh api repos/ale23yfm/evolution-gaming-ro-python-scraper/pages --jq .html_url
curl -s -o /dev/null -w "%{http_code}\n" https://ale23yfm.github.io/evolution-gaming-ro-python-scraper/
```

Expect: `https://ale23yfm.github.io/evolution-gaming-ro-python-scraper/` and HTTP `200`.
The site is built from `docs/` on `main` (source: branch `main`, path `/docs`).

## GitHub Actions

For each workflow in `.github/workflows/`, run it from **Actions** → *Run workflow* (on `main`) and check all jobs are green:

| Workflow | Trigger | Ce verifici |
|----------|---------|-------------|
| `job-seeker-ro-spider.yml` | `workflow_dispatch` | Scraperul rulează → job-uri în API + `docs/jobs.md` generat |
| `automation-testing.yml` | `workflow_dispatch` | Toate testele + validare job-uri |

After a successful run, verify via API that the company jobs appear:

```bash
curl -s "https://api.peviitor.ro/v1/scraper/jobs/?cif=36034853&rows=500"
```

Check `docs/jobs.md` was regenerated and jobs are visible on https://peviitor.ro (CIF `36034853`).
