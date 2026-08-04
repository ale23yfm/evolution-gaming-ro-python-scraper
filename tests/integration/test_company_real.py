"""Integration tests that require live network access (skipped if unavailable).

These are not part of the default CI run and mirror the `itIfSolr`/`itIfAnaf`
conventions from the Node.js template.
"""

import socket

import pytest

from scraper import anaf
from scraper.api import API_BASE_URL
from scraper.config import company_config

COMPANY_CIF = company_config["id"]
COMPANY_NAME = company_config["company"]


def _reachable(host, port=443, timeout=3):
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


@pytest.fixture(scope="module")
def peviitor_api_reachable():
    host = API_BASE_URL.split("://")[1].split("/")[0]
    return _reachable(host)


def test_anaf_returns_company():
    if not _reachable("cuiscan.ro"):
        pytest.skip("cuiscan.ro not reachable")
    company = anaf.get_company_from_anaf(COMPANY_CIF)
    if company is None:
        pytest.skip("ANAF APIs unavailable")
    assert company["denumire"] == COMPANY_NAME
    assert company["cif"] == COMPANY_CIF
    assert company["stareInregistrare"] == "INREGISTRAT"


def test_search_anofm_for_company():
    if not _reachable("mediere.anofm.ro"):
        pytest.skip("mediere.anofm.ro not reachable")
    jobs = anaf.search_anofm(COMPANY_CIF)
    for job in jobs:
        assert job["url"].startswith("https://mediere.anofm.ro/")
        assert job["title"]


def test_peviitor_company_core_exists(peviitor_api_reachable):
    if not peviitor_api_reachable:
        pytest.skip("peviitor API not reachable")
    company = anaf.get_company_from_anaf(COMPANY_CIF)
    if company is None:
        pytest.skip("ANAF APIs unavailable")
    from scraper.api import get_company_by_cif
    result = get_company_by_cif(COMPANY_CIF)
    if result is None:
        pytest.skip("company core not yet created in peviitor")
    assert result
