# Robots

The scraper uses `User-Agent: job_seeker_ro_spider` and only requests public
job listing/detail pages from:

- `https://careers.evolution.com`
- `https://mediere.anofm.ro`
- `https://api.peviitor.ro`
- `https://demoanaf.ro`, `https://cuiscan.ro`, `https://www.cuifirma.ro`

Rate: one listing request + per-job HEAD/content checks only when validating.
No aggressive crawling; respect `robots.txt` when present.
