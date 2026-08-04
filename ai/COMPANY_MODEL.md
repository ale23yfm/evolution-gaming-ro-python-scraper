# Company Model

Company document published to the peviitor company core (`/v1/firme/company/`).

## Source of truth

`scraper/config/company.json` — never edit other copies; they are generated.

## Fields

| Field        | Type   | Description                                                        |
|--------------|--------|--------------------------------------------------------------------|
| `id`         | string | CIF (8 digits, no RO prefix)                                       |
| `company`    | string | Legal name from Trade Register (UPPERCASE, diacritics required)    |
| `brand`      | string | Public brand name                                                  |
| `group`      | string | Parent company group (optional)                                    |
| `status`     | string | `activ` / `suspendat` / `inactiv` / `radiat`                       |
| `location`   | array  | Romanian cities/addresses (diacritics accepted)                    |
| `website`    | array  | Company website (canonical HTTP/HTTPS URL)                         |
| `career`     | array  | Careers/board URL (canonical HTTP/HTTPS URL)                       |
| `lastScraped`| string | Date of last scrape (ISO 8601)                                     |
| `scraperFile`| string | GitHub Actions workflow URL (no raw)                               |

## Notes

- Fields marked `array` are multi-valued arrays stored as arrays in SOLR.
- `status = "activ"` means jobs are kept; otherwise jobs are removed.
- `website` and `career` should be canonical URLs without a trailing slash.
- `scraperFile` must be the full workflow URL, not the raw file URL.

## Upsert behavior

`upsert_company` passes the CIF **as-is** (no zero-padding, per AGENTS.md
commandment 2) and PUTs to `/v1/firme/company/add/`. The live
address/location from ANAF (CUIScan) takes precedence over the static
config when available.

## Example

```json
{
  "id": "36034853",
  "company": "EVOLUTION PRODUCTS RO S.R.L.",
  "brand": "EVOLUTION",
  "status": "activ",
  "location": ["Bucuresti"],
  "website": ["https://www.evolution.com"],
  "career": ["https://careers.evolution.com/romania/en/"],
  "scraperFile": "https://github.com/ale23yfm/evolution-gaming-ro-python-scraper/actions/workflows/job-seeker-ro-spider.yml"
}
```
