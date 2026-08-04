"""Unit tests for config loading and structure."""

import json


def test_company_config_shape(company_config):
    assert company_config["id"].isdigit()
    assert company_config["company"]
    assert company_config["brand"]
    assert company_config["status"] == "activ"
    assert isinstance(company_config["location"], list)
    assert isinstance(company_config["website"], list)
    assert isinstance(company_config["career"], list)
    assert company_config["career"][0]
    owner = get_remote_owner()
    assert owner in company_config["scraperFile"]
    assert "job-seeker-ro-spider.yml" in company_config["scraperFile"]


def get_remote_owner():
    import subprocess
    out = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True)
    owner = out.strip().split("/")[-2]
    assert owner
    return owner


def test_company_config_id_is_numeric(company_config):
    assert company_config["id"].isdigit()


def test_scraper_config_shape(scraper_config):
    assert scraper_config["apiBase"] == "https://careers.evolution.com"
    assert scraper_config["apiPath"] == "/wp-json/wp/v2/vacancies"
    assert scraper_config["jobDetailsPrefix"] == "https://careers.evolution.com/job/"


def test_configs_are_json_files():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2]
    for name in ("company.json", "scraper.json"):
        p = root / "scraper" / "config" / name
        assert p.exists()
        json.loads(p.read_text(encoding="utf-8"))
