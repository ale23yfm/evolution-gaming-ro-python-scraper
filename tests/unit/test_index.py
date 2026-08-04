"""Unit tests for the careers.evolution.com JSON API parser."""

import json

from scraper import index

SAMPLE_VACANCIES = [
    {
        "id": 12345,
        "name": "Entry Level Game Presenter",
        "refNumber": "REF1898P",
        "location": {
            "city": "Bucharest",
            "region": "Bucharest",
            "country": "RO",
            "fullLocation": "Bucharest, Bucharest, Romania",
            "remote": False,
            "hybrid": False,
        },
        "department": {"label": "Operations"},
    },
    {
        "id": 67890,
        "name": "HR Administrative Specialist",
        "refNumber": "REF5717H",
        "location": {
            "city": "Bucharest",
            "country": "ro",
            "fullLocation": "Bucharest, Bucharest, Romania",
            "remote": True,
            "hybrid": False,
        },
    },
    {
        "id": 99999,
        "name": "Game Presenter — Sofia",
        "refNumber": "REF7788X",
        "location": {
            "city": "Sofia",
            "country": "BG",
            "fullLocation": "Sofia, Bulgaria",
        },
    },
]

CIF = "36034853"
COMPANY = "EVOLUTION PRODUCTS RO S.R.L."


def test_build_listing_url(scraper_config):
    url = index.build_listing_url()
    assert url.startswith("https://")
    assert "careers.evolution.com" in url
    assert "wp-json/wp/v2/vacancies" in url
    assert "nocache=" in url


def test_build_job_url():
    assert index.build_job_url(12345) == "https://careers.evolution.com/job/12345"


def test_build_job_url_preserves_job_id():
    assert index.build_job_url("REF1898P") == "https://careers.evolution.com/job/REF1898P"


def test_extract_location_takes_first_token_and_aliases_bucharest():
    assert index.extract_location("Bucharest, Bucharest, Romania") == ["Bucuresti"]
    assert index.extract_location("Cluj-Napoca, Cluj, Romania") == ["Cluj-Napoca"]


def test_extract_location_single_token():
    assert index.extract_location("Romania") == ["România"]


def test_extract_location_missing():
    assert index.extract_location(None) == []
    assert index.extract_location("") == []


def test_parse_api_jobs_ro_only():
    jobs = index.parse_api_jobs(SAMPLE_VACANCIES)
    assert len(jobs) == 2
    by_url = {j["url"]: j for j in jobs}
    first = by_url["https://careers.evolution.com/job/12345"]
    assert first["title"] == "Entry Level Game Presenter"
    assert first["location"] == ["Bucuresti"]
    assert first["tags"] == ["Operations"]
    assert "https://careers.evolution.com/job/99999" not in by_url


def test_parse_api_jobs_workmode_flags():
    jobs = index.parse_api_jobs(SAMPLE_VACANCIES)
    by_url = {j["url"]: j for j in jobs}
    assert by_url["https://careers.evolution.com/job/67890"]["workmode"] == "remote"
    assert by_url["https://careers.evolution.com/job/12345"]["workmode"] == "on-site"


def test_parse_api_jobs_deduplicates():
    jobs = index.parse_api_jobs(SAMPLE_VACANCIES + SAMPLE_VACANCIES)
    assert len(jobs) == 2


def test_parse_api_jobs_empty():
    assert index.parse_api_jobs(None) == []
    assert index.parse_api_jobs([]) == []


def test_parse_api_jobs_skips_missing_id_or_title():
    bad = [
        {"id": "", "name": "No Id", "location": {"country": "ro", "city": "Bucharest"}},
        {"id": 42, "name": "", "location": {"country": "ro", "city": "Bucharest"}},
    ]
    assert index.parse_api_jobs(bad) == []


def test_map_to_job_model_adds_company_and_status():
    raw = {"url": "https://careers.evolution.com/job/12345",
           "title": "Entry Level Game Presenter", "location": ["Bucuresti"],
           "workmode": "on-site", "tags": ["Operations"]}
    index.COMPANY_NAME = COMPANY
    job = index.map_to_job_model(raw, CIF)
    assert job["company"] == COMPANY
    assert job["cif"] == CIF
    assert job["status"] == "scraped"
    assert job["location"] == ["Bucuresti"]
    assert job["workmode"] == "on-site"
    assert job["tags"] == ["Operations"]


def test_transform_jobs_for_solr_keeps_required_fields():
    jobs = [{"url": "https://careers.evolution.com/job/12345", "title": "Test Job",
             "location": ["Cluj-Napoca"], "company": COMPANY, "cif": CIF}]
    transformed = index.transform_jobs_for_solr({"company": COMPANY, "jobs": jobs})
    assert len(transformed["jobs"]) == 1
    t = transformed["jobs"][0]
    assert t["url"]
    assert t["title"]
    assert t["location"] == ["Cluj-Napoca"]
    assert t["company"] == COMPANY.upper()


def test_transform_workmode_normalized():
    jobs = [{"url": "https://careers.evolution.com/job/1", "title": "Dev",
             "location": ["Cluj-Napoca"], "workmode": "Remote"}]
    transformed = index.transform_jobs_for_solr({"company": COMPANY, "jobs": jobs})
    assert transformed["jobs"][0]["workmode"] == "remote"


def test_transform_missing_workmode_dropped():
    jobs = [{"url": "https://careers.evolution.com/job/1", "title": "Dev",
             "location": ["Cluj-Napoca"]}]
    transformed = index.transform_jobs_for_solr({"company": COMPANY, "jobs": jobs})
    assert "workmode" not in transformed["jobs"][0]


def test_generate_jobs_markdown(tmp_path, company_config):
    jobs = [{"url": "https://careers.evolution.com/job/12345", "title": "Game Presenter",
             "company": COMPANY, "cif": CIF,
             "location": ["Bucuresti"], "workmode": "on-site"}]
    md = index.generate_jobs_markdown(company_config, jobs)
    assert f"# {company_config['company']}" in md
    assert "## Jobs (1)" in md
    assert "Game Presenter" in md
    assert "](https://careers.evolution.com/job/12345)" in md


def test_generate_jobs_markdown_empty():
    md = index.generate_jobs_markdown({}, [])
    assert "## Jobs (0)" in md
    assert "_No jobs found._" in md


def test_main_dry_run_writes_summary(tmp_path, monkeypatch):
    fake_jobs = [{"url": f"https://careers.evolution.com/job/{i}", "title": f"Job {i}",
                  "location": ["Bucuresti"]}
                 for i in range(3)]
    monkeypatch.setattr(index, "parse_api_jobs", lambda vacancies: fake_jobs)
    monkeypatch.setattr(index, "fetch_listing", lambda: SAMPLE_VACANCIES)
    monkeypatch.setattr(index, "query_solr", lambda cif: {"numFound": 1, "docs": []})
    monkeypatch.setattr(index, "upsert_jobs", lambda jobs: None)
    monkeypatch.setattr(index, "delete_job_by_url", lambda url: None)
    monkeypatch.setattr(index, "upsert_company", lambda cfg: None)
    monkeypatch.setattr(index, "validate_and_get_company", lambda: {
        "company": COMPANY, "cif": CIF, "status": "active",
        "address": "BUCHAREST"})
    monkeypatch.setattr(index, "search_anofm", lambda cif: [])

    index.main(root=tmp_path)
    out = tmp_path / "scraper" / "jobs.json"
    assert out.exists()
    data = json.loads(out.read_text())
    assert len(data["jobs"]) >= 3
