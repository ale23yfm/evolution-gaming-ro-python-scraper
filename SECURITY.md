# Security Policy

## Reporting a Vulnerability

Do **not** open a public issue. Report vulnerabilities privately via GitHub
security advisories on this repository.

We will acknowledge the report within 5 business days and work on a fix before
disclosure.

## Scope

- Credentials and tokens: never commit secrets. API interactions use the
  public `job_seeker_ro_spider` user agent only.
- Cache files: `scraper/anaf_cache.json` is git-ignored and contains only
  public company data.
