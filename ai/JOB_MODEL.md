# Job Model

Standardized job document published to peviitor SOLR.

## Fields

| Field           | Required | Description                                                        |
|-----------------|----------|--------------------------------------------------------------------|
| `url`           | yes      | Canonical job URL (valid HTTP/HTTPS)                               |
| `title`         | yes      | Position title — max 200 chars, no HTML, trimmed whitespace        |
| `company`       | no       | Company name (UPPERCASE, diacritics allowed)                       |
| `cif`           | no       | Company CIF, as-is (8 digits, no zero-padding)                     |
| `location`      | no       | Array of Romanian cities (diacritics accepted)                     |
| `tags`          | no       | Lowercase keywords, max 20 entries, NO diacritics                  |
| `workmode`      | no       | `remote` / `on-site` / `hybrid`                                     |
| `date`          | no       | ISO 8601 (`YYYY-MM-DDThh:mm:ssZ`)                                   |
| `status`        | no       | `scraped`                                                           |
| `vdate`         | no       | Verification date (ISO)                                             |
| `expirationdate`| no       | Expiration date (ISO)                                               |
| `salary`        | no       | Salary info as string, e.g. `"5000-8000 RON"` (not an array)        |

## Status flow

`scraped` → (`tested` OR `verified`) → `published`

| Status    | Meaning                                                           |
|-----------|-------------------------------------------------------------------|
| scraped   | Newly scraped, not validated yet                                  |
| tested    | URL works, job exists but incomplete details                      |
| verified  | Fully scraped with all details                                    |
| published | Imported from jobs core                                           |

## Location rules

- Only Romanian cities accepted; non-Romanian entries are dropped.
- If no valid city remains, the location falls back to `["România"]`.
- `"Romania"` (ASCII) is normalized to `"România"`.
- Cities come from `extract_location` (first token of `"City, County, Romania"`).

## Workmode rules

`_normalize_workmode` maps:

- contains `remote` → `remote`
- contains `office` / `on-site` / `site` → `on-site`
- otherwise → `hybrid` (or omitted when unknown)

## Example

```json
{
  "url": "https://careers.evolution.com/job/12345",
  "title": "Entry Level Game Presenter",
  "company": "EVOLUTION PRODUCTS RO S.R.L.",
  "cif": "36034853",
  "location": ["Bucuresti"],
  "workmode": "on-site",
  "date": "2026-08-03T00:00:00Z",
  "status": "scraped"
}
```
