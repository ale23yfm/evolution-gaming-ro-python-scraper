"""
EVOLUTION (EVOLUTION PRODUCTS RO S.R.L.) Scraper — derived from the
E-INFRA Python template.

Scrapes EVOLUTION job listings from the careers.evolution.com WordPress
REST API (wp-json/wp/v2/vacancies) filtered to Romania, validates the
company via ANAF, and publishes jobs/company data to peviitor.ro through
the v1 API (api.peviitor.ro/v1) — no direct Solr access.
"""

import datetime
import json
import pathlib
import sys
import time

import requests

from .anaf import search_anofm
from .api import delete_job_by_url, delete_jobs_by_cif, query_solr, upsert_company, upsert_jobs
from .company import validate_and_get_company
from .config import company_config, scraper_config
from .markdown_generator import generate_jobs_markdown

TIMEOUT = 10
HEADERS = {"User-Agent": "job_seeker_ro_spider"}

COMPANY_CIF = company_config["id"]
API_BASE = scraper_config["apiBase"]
API_PATH = scraper_config["apiPath"]

COMPANY_NAME = None

# Jobs stored in SOLR under this CIF may be published by other peviitor
# scrapers (aggregators). Stale deletion must only ever touch jobs that this
# scraper itself published (i.e. URLs on the Evolution careers board), so we
# scope it to this prefix instead of the whole CIF.
JOB_DETAILS_PREFIX = scraper_config["jobDetailsPrefix"]

# Map Evolution's English city names to the Romanian names used on peviitor.ro.
_CITY_ALIASES = {
    "bucharest": "Bucuresti",
}


def build_listing_url():
    """Builds the vacancies API URL with a cache-busting query string."""
    return f"{API_BASE}{API_PATH}?nocache={int(time.time())}"


def build_job_url(job_id):
    """Builds the canonical job detail URL.

    careers.evolution.com redirects the no-slash form (301) to the trailing-
    slash URL. Validators treat any 3xx as expired, so we must store the
    canonical form: 200 for a live job, 404 for a removed one.
    """
    return f"{API_BASE}/job/{job_id}/"


def extract_location(location_text):
    """Extracts the city from a location string like 'Bucharest, Bucharest, Romania'."""
    if not location_text:
        return []
    first = location_text.split(",")[0].strip()
    if not first:
        return []
    if first.lower() in ("romania", "românia", "romania -"):
        return ["România"]
    normalized = _normalize_city(first)
    if normalized in _CITY_ALIASES:
        return [_CITY_ALIASES[normalized]]
    return [first]


def _normalize_workmode(raw):
    """Normalizes a workmode string to remote / hybrid / on-site."""
    if not raw:
        return None
    lower = raw.lower()
    if "remote" in lower:
        return "remote"
    if "office" in lower or "on-site" in lower or "site" in lower:
        return "on-site"
    return "hybrid"


def parse_api_jobs(vacancies):
    """Parses the careers.evolution.com vacancies JSON into raw job dicts (RO only)."""
    jobs = []
    seen_ids = set()

    if not isinstance(vacancies, list):
        return jobs

    for vacancy in vacancies or []:
        if not isinstance(vacancy, dict):
            continue
        loc = vacancy.get("location") or {}
        if not isinstance(loc, dict):
            loc = {}
        if (loc.get("country") or "").lower() != "ro":
            continue
        job_id = str(vacancy.get("id") or "").strip()
        if not job_id or job_id in seen_ids:
            continue
        seen_ids.add(job_id)

        title = (vacancy.get("name") or "").strip()
        if not title:
            continue

        full_location = loc.get("fullLocation")
        location = extract_location(full_location)
        if not location:
            location = ["România"]

        if loc.get("remote"):
            workmode = "remote"
        elif loc.get("hybrid"):
            workmode = "hybrid"
        else:
            workmode = "on-site"

        raw = {
            "url": build_job_url(job_id),
            "title": title,
            "location": location,
            "workmode": workmode,
        }
        department = (vacancy.get("department") or {}).get("label")
        if department:
            raw["tags"] = [department]

        jobs.append(raw)

    return jobs


def fetch_listing():
    """Fetches the vacancies JSON payload for the company."""
    url = build_listing_url()
    res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if res.status_code != 200:
        raise RuntimeError(f"Listing error: {res.status_code} for {url}")
    return res.json()


def map_to_job_model(raw_job, cif, company_name=None):
    """Maps a raw job dict to the standardized job model."""
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    job = {
        "url": raw_job["url"],
        "title": raw_job["title"],
        "company": company_name or COMPANY_NAME,
        "cif": cif,
        "date": now,
        "status": "scraped",
    }
    if raw_job.get("location"):
        job["location"] = raw_job["location"]
    if raw_job.get("workmode"):
        job["workmode"] = raw_job["workmode"]
    if raw_job.get("tags"):
        job["tags"] = raw_job["tags"]
    return job


_ROMANIAN_CITIES = [
    "Bucharest", "București", "Bucuresti", "Cluj-Napoca", "Cluj Napoca",
    "Timișoara", "Timisoara", "Iași", "Iasi", "Brașov", "Brasov",
    "Constanța", "Constanta", "Craiova", "Bacău", "Sibiu",
    "Târgu Mureș", "Targu Mures", "Oradea", "Baia Mare", "Satu Mare",
    "Ploiești", "Ploiesti", "Pitești", "Pitesti", "Arad", "Galați", "Galati",
    "Brăila", "Braila", "Drobeta-Turnu Severin", "Râmnicu Vâlcea", "Ramnicu Valcea",
    "Buzău", "Buzau", "Botoșani", "Botosani", "Zalău", "Zalau", "Hunedoara", "Deva",
    "Suceava", "Bistrița", "Bistrita", "Tulcea", "Călărași", "Calarasi",
    "Giurgiu", "Alba Iulia", "Slatina", "Piatra Neamț", "Piatra Neamt",
    "Piatra-Neamt", "Roman", "Turda", "Câmpia Turzii", "Campia Turzii",
    "Medgidia", "Gura Ialomiței", "Gura Ialomitei",
    "Dumbrăvița", "Dumbravita", "Voluntari", "Popești-Leordeni", "Popesti-Leordeni",
    "Chitila", "Mogoșoaia", "Mogosoaia", "Otopeni",
]

_DIACRITIC_MAP = str.maketrans("ăâîșțĂÂÎȘȚ", "aaistAAIST")


def _normalize_city(city):
    """Normalizes a city name: lowercase, no diacritics, no hyphen/double spaces."""
    if not city:
        return ""
    normalized = city.lower().translate(_DIACRITIC_MAP)
    return " ".join(normalized.replace("-", " ").split())


_CITY_SET = {_normalize_city(c) for c in _ROMANIAN_CITIES}


def transform_jobs_for_solr(payload):
    """Filters jobs to Romanian cities and normalizes workmode."""
    company = (payload.get("company") or "").upper()

    transformed_jobs = []
    for job in payload.get("jobs", []):
        locations = []
        for loc in job.get("location") or []:
            normalized = _normalize_city(loc)
            if normalized in ("romania", "românia"):
                locations.append("România")
            elif normalized in _CITY_SET:
                locations.append(loc)
        new_job = {
            **job,
            "location": locations if locations else ["România"],
            "workmode": _normalize_workmode(job.get("workmode")),
        }
        if new_job["workmode"] is None:
            del new_job["workmode"]
        transformed_jobs.append(new_job)

    return {**payload, "company": company, "jobs": transformed_jobs}


def scrape_all_listings():
    """Fetches and parses all jobs for the company."""
    return parse_api_jobs(fetch_listing())


def main(root=None):
    test_only_one_page = "--test" in sys.argv
    root = root or pathlib.Path(__file__).resolve().parents[1]

    print("=== Step 1: Get existing jobs from SOLR ===")
    existing_result = query_solr(COMPANY_CIF)
    existing_count = existing_result["numFound"]
    existing_urls = {doc.get("url") for doc in existing_result["docs"]
                     if doc.get("url") and doc["url"].startswith(JOB_DETAILS_PREFIX)}
    print(f"Found {existing_count} existing jobs in SOLR ({len(existing_urls)} from this board)")

    print("=== Step 2: Validate company via ANAF ===")
    validated = validate_and_get_company()
    global COMPANY_NAME
    COMPANY_NAME = validated["company"]
    if validated["status"] == "inactive":
        print("⚠️ Company is INACTIVE — deleting jobs and skipping scrape.")
        try:
            delete_jobs_by_cif(validated["cif"])
            print(f"✅ Deleted all jobs for CIF {validated['cif']}")
        except Exception as del_err:
            print(f"⚠️ Failed to delete jobs for CIF {validated['cif']}: {del_err}")
        return

    try:
        upsert_company({
            "id": validated["cif"],
            "company": validated["company"],
            "brand": company_config.get("brand"),
            "status": "activ",
            "location": [validated["address"]] if validated["address"] else company_config["location"],
            "website": company_config.get("website"),
            "career": company_config.get("career"),
            "scraperFile": company_config.get("scraperFile"),
            "lastScraped": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        })
    except Exception as err:
        print(f"Note: Could not upsert company: {err}")

    raw_jobs = scrape_all_listings()
    scraped_count = len(raw_jobs)
    print(f"Jobs scraped from the EVOLUTION careers board: {scraped_count}")

    if not test_only_one_page:
        anofm_jobs = search_anofm(validated["cif"])
        anofm_count = len(anofm_jobs)
        known_urls = {j["url"] for j in raw_jobs}
        for job in anofm_jobs:
            if job["url"] not in known_urls:
                raw_jobs.append(job)
                known_urls.add(job["url"])
        print(f"Jobs added from ANOFM: {anofm_count}")

    jobs = [map_to_job_model(job, validated["cif"]) for job in raw_jobs]

    payload = {
        "source": "careers.evolution.com",
        "scrapedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "company": COMPANY_NAME,
        "cif": validated["cif"],
        "jobs": jobs,
    }

    print("Transforming jobs for SOLR...")
    transformed_payload = transform_jobs_for_solr(payload)
    valid_count = len([j for j in transformed_payload["jobs"] if j.get("location")])
    print(f"Jobs with valid Romanian locations: {valid_count}")

    # jobs.json
    jobs_path = root / "scraper" / "jobs.json"
    jobs_path.parent.mkdir(parents=True, exist_ok=True)
    jobs_path.write_text(
        json.dumps(transformed_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved scraper/jobs.json")

    company_data = {
        "id": validated["cif"],
        "company": transformed_payload["company"],
        "brand": company_config.get("brand"),
        "status": "activ",
        "location": [validated["address"]] if validated["address"] else company_config["location"],
        "website": company_config.get("website"),
        "career": company_config.get("career"),
        "lastScraped": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    }
    markdown = generate_jobs_markdown(company_data, transformed_payload["jobs"])
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "jobs.md").write_text(markdown, encoding="utf-8")
    print("Saved docs/jobs.md")

    src_company = pathlib.Path(__file__).resolve().parent / "config" / "company.json"
    (root / "docs" / "company.json").write_text(src_company.read_text(encoding="utf-8"), encoding="utf-8")
    print("Copied scraper/config/company.json → docs/company.json")

    print("\n=== Step 4: Upsert jobs to SOLR ===")
    upsert_jobs(transformed_payload["jobs"])

    scraped_urls = {job["url"] for job in transformed_payload["jobs"]}
    stale_urls = [url for url in existing_urls if url not in scraped_urls]

    if stale_urls:
        print(f"\n=== Step 4.5: Delete {len(stale_urls)} stale job(s) ===")
        deleted_count = 0
        for url in stale_urls:
            try:
                print(f"  Deleting: {url}")
                delete_job_by_url(url)
                deleted_count += 1
            except Exception as del_err:
                print(f"  ⚠️ Failed to delete: {url} — {del_err}")
        print(f"✅ Deleted {deleted_count}/{len(stale_urls)} stale job(s)")
    else:
        print("\n✅ No stale jobs to delete")

    print("\n=== Step 5: Summary ===")
    time.sleep(2)
    final_result = query_solr(COMPANY_CIF)
    print(f"\n=== SUMMARY ===")
    print(f"Jobs existing in SOLR before scrape: {existing_count}")
    print(f"Jobs scraped from the EVOLUTION careers board: {scraped_count}")
    print(f"Stale jobs attempted: {len(stale_urls)}")
    print(f"Jobs in SOLR after scrape: {final_result['numFound']}")
    print(f"====================")

    print("\n=== DONE ===")
    print("Scraper completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print("Scraper failed:", err)
        sys.exit(1)
