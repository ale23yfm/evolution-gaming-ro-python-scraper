import json
import pathlib
import sys
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest

import scraper.api as api


@pytest.fixture
def company_config():
    with open(ROOT / "scraper" / "config" / "company.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def scraper_config():
    with open(ROOT / "scraper" / "config" / "scraper.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def _mock_api_timeout(monkeypatch):
    """Speed up tests that hit real endpoints by lowering timeouts."""
    def _fast_requests(method, url, **kwargs):
        kwargs.setdefault("timeout", 10)
        return api.requests.request(method, url, **kwargs)
    monkeypatch.setattr(api.requests, "request", _fast_requests)


def _make_response(status_code=200, payload=None, ok=True, text=""):
    res = mock.Mock()
    res.status_code = status_code
    res.ok = ok
    res.text = text
    res.json.return_value = payload if payload is not None else {}
    return res


@pytest.fixture
def mock_get(monkeypatch):
    m = mock.Mock(return_value=_make_response())
    monkeypatch.setattr(api.requests, "get", m)
    return m


@pytest.fixture
def mock_post(monkeypatch):
    m = mock.Mock(return_value=_make_response())
    monkeypatch.setattr(api.requests, "post", m)
    return m


@pytest.fixture
def mock_put(monkeypatch):
    m = mock.Mock(return_value=_make_response())
    monkeypatch.setattr(api.requests, "put", m)
    return m


@pytest.fixture
def mock_delete(monkeypatch):
    m = mock.Mock(return_value=_make_response())
    monkeypatch.setattr(api.requests, "delete", m)
    return m


@pytest.fixture
def mock_head(monkeypatch):
    m = mock.Mock(return_value=_make_response())
    monkeypatch.setattr(api.requests, "head", m)
    return m
