"""
Job URL Validation Module

Shared validation primitives used by validate_jobs.py and CI workflows.
"""

import re
from urllib.parse import urlsplit

import requests

HEADERS = {"User-Agent": "job_seeker_ro_spider"}
TIMEOUT = 10

_DISABLED_TAG_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.S | re.I)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _visible_text(html):
    """Lowercased visible text, with script/style blocks and tags stripped.

    Boards bundle JS that contains words like "removed"/"expired" (e.g.
    applytojob's "xhr-load-removed"); matching against raw HTML would flag
    active jobs as expired.
    """
    text = _DISABLED_TAG_RE.sub(" ", html or "")
    text = _HTML_TAG_RE.sub(" ", text)
    return text.lower()


DEFAULT_EXPIRED_KEYWORDS = [
    "not found",
    "no longer accepting",
    "position has been filled",
    "position is no longer",
    "has expired",
    "expired",
    "removed",
    "job is no longer available",
    "this position has been filled",
]


def validate_by_head(url):
    """Returns active/expired/error based on a HEAD request.

    A 3xx redirect is treated as expired: job boards redirect closed jobs
    (applytojob returns a 302 to the jobs list). Redirects are not followed.
    """
    try:
        res = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=False)
        if res.status_code == 200:
            return {"url": url, "status": "active", "http_status": res.status_code}
        return {"url": url, "status": "expired", "http_status": res.status_code}
    except Exception as err:
        return {"url": url, "status": "error", "error": str(err)}


def validate_by_content(url, keywords=None, timeout=TIMEOUT):
    """Returns active/expired based on page content keywords.

    A redirect (3xx) is treated as expired — closed jobs are redirected to the
    jobs list instead of returning a real 404.
    """
    keywords = keywords or DEFAULT_EXPIRED_KEYWORDS
    try:
        res = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=False)
        if res.status_code != 200:
            return {"url": url, "status": "expired", "http_status": res.status_code}
        body = _visible_text(res.text)
        for kw in keywords:
            if kw.lower() in body:
                return {"url": url, "status": "expired", "http_status": res.status_code}
        return {"url": url, "status": "active", "http_status": res.status_code}
    except Exception as err:
        return {"url": url, "status": "error", "error": str(err)}


def validate_by_browser(url, timeout=30000):
    """Returns active/expired using a real browser (catches JS-based 404s).

    Requires Playwright (python3 -m playwright install chromium).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"url": url, "status": "error", "error": "playwright not installed"}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            final_url = page.url
            body = _visible_text(page.content())
            browser.close()
        if response and response.status != 200:
            return {"url": url, "status": "expired", "http_status": response.status}
        orig_path = urlsplit(url).path
        final_path = urlsplit(final_url).path
        if orig_path != final_path:
            return {"url": url, "status": "expired", "http_status": response.status if response else None}
        for kw in DEFAULT_EXPIRED_KEYWORDS:
            if kw.lower() in body:
                return {"url": url, "status": "expired", "http_status": response.status if response else None}
        return {"url": url, "status": "active", "http_status": response.status if response else None}
    except Exception as err:
        return {"url": url, "status": "error", "error": str(err)}
