"""
deduplicate.py — CLI tool that removes duplicate job listings from SOLR.

Duplicate listings are jobs stored under different URLs that, after following
redirects, land on the same final page (e.g. aggregator URLs such as
jobviewtrack.com that 302 to the same careerjet.ro jobad).

Usage:
  python -m scraper.deduplicate <COMPANY> [--dry-run] [--delete] [--workers 8]
                                       [--limit N] [--wait SECONDS] [--cache PATH]
                                       [--cif CIF] [--company-name NAME]

Read-only by default. With ``--delete`` the duplicate listings of a group are
removed (one listing per final URL is always kept) and each kept listing is
re-attributed (upserted) with the CIF and company name from the company model.
``--cache PATH`` persists resolved URL keys so re-runs skip network lookups.
"""

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import requests

from .api import API_BASE_URL, HEADERS, delete_job_by_url, upsert_jobs
from .config import company_config, scraper_config

SEARCH_ROWS = 500
TIMEOUT = 15

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
}

_CAREERJET_ID = re.compile(r"careerjet\.ro/(?:clk/|jobad/ro)([0-9a-f]{20,})\.?(?:html)?", re.IGNORECASE)

BOARD_PREFIX = scraper_config.get("jobDetailsPrefix") or f"{scraper_config['apiBase']}/apply/jobs/details/"

_thread_local = threading.local()


def _session():
    """Returns a per-thread requests session (Session is not thread-safe)."""
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        _thread_local.session = session
    return session


class UrlCache:
    """Persists resolved URL keys (url -> key) to a JSON file.

    Avoids re-resolving the same redirecting URLs on every run, which keeps
    re-runs fast and reduces the load on rate-limited aggregators.
    """

    def __init__(self, path):
        self.path = path
        self.data = {}
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except (OSError, ValueError):
            self.data = {}

    def get(self, url):
        value = self.data.get(url)
        if not value:
            return None
        return value["key"], value["kind"], value["final"]

    def set(self, url, key, kind, final):
        self.data[url] = {"key": key, "kind": kind, "final": final}

    def save(self):
        if not self.path:
            return
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)


def search_jobs(company, rows=SEARCH_ROWS):
    """Fetches all job docs for a company via the peviitor search API (paginated)."""
    docs = []
    page = 1
    while True:
        res = requests.get(
            f"{API_BASE_URL}/search/",
            params={"company": company, "page": page, "rows": rows},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        if res.status_code != 200:
            raise RuntimeError(f"API search error: {res.status_code} - {res.text}")
        data = res.json().get("response", {})
        batch = data.get("docs") or []
        docs.extend(batch)
        total = data.get("numFound", 0)
        if not batch or page * rows >= total:
            break
        page += 1
    return docs


_throttle_lock = threading.Lock()
_last_request_at = [0.0]


def _throttle(wait):
    """Sleeps so that consecutive resolution calls are at least ``wait`` seconds apart."""
    if not wait:
        return
    with _throttle_lock:
        elapsed = time.time() - _last_request_at[0]
        delay = wait - elapsed
        if delay > 0:
            time.sleep(delay)
        _last_request_at[0] = time.time()


def resolve_key(url, cache=None, wait=0):
    """Returns a stable key for a job URL after following redirects.

    Aggregator URLs (jobviewtrack.com) 302 to a careerjet.ro jobad; the jobad
    id identifies the job, so all listings for the same job share the same key.
    Returns a tuple (key, kind, final_url); kind is one of
    "careerjet", "redirect", "direct", "unresolved".
    """
    if cache:
        hit = cache.get(url)
        if hit:
            return hit

    session = _session()
    for attempt in range(2):
        _throttle(wait)
        try:
            res = session.head(url, headers=BROWSER_HEADERS, allow_redirects=False, timeout=5)
        except Exception as err:
            return url, "unresolved", f"error: {err}"
        if res.status_code == 429:
            if attempt == 0:
                time.sleep(1)
                continue
            return url, "unresolved", "rate-limited"
        location = res.headers.get("Location")
        if location:
            m = _CAREERJET_ID.search(location)
            if m:
                key = f"careerjet:{m.group(1)}"
            else:
                key = location.rstrip("/")
            kind = "careerjet" if key.startswith("careerjet:") else "redirect"
        else:
            key, kind = url.rstrip("/"), "direct"
            location = url
        if cache:
            cache.set(url, key, kind, location)
        return key, kind, location
    return url, "unresolved", "rate-limited"


def pick_keeper(members):
    """Selects the listing to keep from a duplicate group.

    Prefers URLs under our board prefix (jobs we publish with canonical URLs),
    otherwise the first member.
    """
    def rank(doc):
        return 0 if doc.get("url", "").startswith(BOARD_PREFIX) else 1

    return min(members, key=rank)


def find_duplicates(docs, workers=8, cache=None, wait=0):
    """Groups job docs by their resolved final URL and returns duplicate groups.

    Each group dict has the shape:
      {"key": ..., "final_url": ..., "keeper": doc, "duplicates": [docs]}
    """
    urls = [doc.get("url", "") for doc in docs]
    resolve = partial(resolve_key, cache=cache, wait=wait)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        keys = list(pool.map(resolve, urls))

    groups = {}
    for doc, (key, kind, final) in zip(docs, keys):
        groups.setdefault(key, {"kind": kind, "final_url": final, "members": []})
        groups[key]["members"].append(doc)

    duplicates = []
    for key, info in groups.items():
        members = info["members"]
        if len(members) <= 1:
            continue
        keeper = pick_keeper(members)
        dupes = [doc for doc in members if doc is not keeper]
        duplicates.append({
            "key": key,
            "final_url": info["final_url"],
            "keeper": keeper,
            "duplicates": dupes,
        })
    return duplicates


def main(argv=None):
    parser = argparse.ArgumentParser(description="Remove duplicate jobs that resolve to the same final URL")
    parser.add_argument("company", help="Company/brand name as indexed in SOLR (e.g. 'EVOLUTION GAMING')")
    parser.add_argument("--dry-run", action="store_true", help="Do not delete anything")
    parser.add_argument("--delete", action="store_true", help="Delete duplicates and re-attribute the kept listings")
    parser.add_argument("--workers", type=int, default=8, help="Parallel redirect resolutions")
    parser.add_argument("--limit", type=int, default=0, help="Process at most N docs (0 = all)")
    parser.add_argument("--wait", type=float, default=0,
                        help="Seconds to wait between URL resolutions (avoid rate limiting)")
    parser.add_argument("--cache", default=None,
                        help="Persist resolved URL keys to PATH so re-runs skip network lookups")
    parser.add_argument("--cif", default=company_config["id"], help="CIF for kept listings (default: company model)")
    parser.add_argument("--company-name", default=company_config["company"],
                        help="Company name for kept listings (default: company model)")
    args = parser.parse_args(argv)

    print(f"Fetching jobs for company '{args.company}'...")
    docs = search_jobs(args.company)
    if args.limit:
        docs = docs[:args.limit]
    print(f"Total docs in SOLR: {len(docs)}")

    cache = UrlCache(args.cache) if args.cache else None
    duplicates = find_duplicates(docs, workers=args.workers, cache=cache, wait=args.wait)
    if cache:
        cache.save()
    to_remove = sum(len(g["duplicates"]) for g in duplicates)
    print(f"Duplicate groups: {len(duplicates)} ({to_remove} listings to remove, one per group kept)\n")

    if not duplicates:
        print("✅ No duplicates found.")
        return 0

    for i, group in enumerate(duplicates, start=1):
        print(f"[{i}/{len(duplicates)}] final: {group['final_url']}")
        print(f"    keep:   {group['keeper'].get('url')} (cif={args.cif}, company={args.company_name})")
        for dup in group["duplicates"]:
            print(f"    remove: {dup.get('url')}")

    print(f"\n⚠️ {to_remove} duplicate listing(s) in {len(duplicates)} group(s).")
    if args.dry_run:
        print("Dry run — nothing deleted.")
        return 0
    if not args.delete:
        print("Use --delete to remove them, or --dry-run to preview.")
        return 1

    for group in duplicates:
        keeper = group["keeper"]
        keeper["cif"] = args.cif
        keeper["company"] = args.company_name

    deleted = 0
    for group in duplicates:
        for dup in group["duplicates"]:
            url = dup.get("url", "")
            try:
                delete_job_by_url(url)
                deleted += 1
            except Exception as err:
                print(f"  ⚠️ Failed to delete {url}: {err}")
    print(f"✅ Deleted {deleted} duplicate listing(s) via API.")

    upsert_jobs([group["keeper"] for group in duplicates])
    print(f"✅ Re-attributed {len(duplicates)} kept listing(s) to cif={args.cif} / company={args.company_name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
