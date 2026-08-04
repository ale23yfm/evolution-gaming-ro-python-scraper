# BRANCH.md — Default Branch Must Be `main`

All scrapers derived from the template **MUST** use `main` as the default branch.

## De ce `main`?

- `master` este o denumire veche (legacy); GitHub recomandă `main` din 2020
- Toate repo-urile noi pe GitHub au `main` ca default
- Consistență între toate scraper-ele

## Reguli

1. Default branch **MUST** fie `main` — NU `master`, `develop`, sau altceva.
2. Orice branch `master` existent trebuie redenumit în `main`.
3. Verificare: `gh repo view ale23yfm/evolution-gaming-ro-python-scraper --json defaultBranch`
4. Doar `main` este long-lived; munca se face pe branch-uri scurte sau direct
   prin GitHub Actions (repo-ul e condus de workflows programate).

## Cum redenumești

```bash
# Creează branch-ul main pe același commit ca master
gh api repos/ale23yfm/evolution-gaming-ro-python-scraper/git/refs -f ref="refs/heads/main" -f sha=$(gh api repos/ale23yfm/evolution-gaming-ro-python-scraper/git/refs/heads/master --jq '.object.sha')

# Schimbă default branch
gh api repos/ale23yfm/evolution-gaming-ro-python-scraper -X PATCH -f default_branch="main"

# Șterge branch-ul master
gh api repos/ale23yfm/evolution-gaming-ro-python-scraper/git/refs/heads/master -X DELETE
```
