# Issues

Acest proiect folosește [GitHub Issues](https://github.com/ale23yfm/evolution-gaming-ro-python-scraper/issues) pentru a urmări munca.

## Regulă

**Orice modificare de cod trebuie să aibă un issue corespunzător în GitHub Issues.**

Excepții:
- Corecturi minore (typo-uri, whitespace, comentarii)
- Changeset-uri care rezolvă un issue existent

## Flux

1. Creăm un issue care descrie ce trebuie făcut
2. Implementăm modificarea
3. Commit-ul menționează issue-ul (ex: `#7`)
4. Închidem issue-ul cu un comentariu care link-uiește commit-ul

## Issue-uri deschise

Vezi [toate issue-urile](https://github.com/ale23yfm/evolution-gaming-ro-python-scraper/issues).

## Common issues

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `0` jobs parsed | Board HTML changed | Update selectors in `scraper/index.py` |
| Company INACTIVE | ANAF status change | Do not scrape; jobs get deleted |
| API 401/403 | Token/endpoint change | Check `scraper/api.py` |
| Tests fail offline | Network-dependent test | Ensure `pytest.skip` on unreachable hosts |
| Validator flags live jobs EXPIRED | Keyword hit inside bundled JS | Content check strips `<script>`/`<style>` — check `scraper/job_validator.py` |

## Escalation

For peviitor API problems, contact the peviitor maintainers with the CIF
`36034853` and the failing endpoint.
