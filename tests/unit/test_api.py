import tests.conftest  # noqa: F401  (sys.path setup)
import unittest.mock as mock

import pytest

import scraper.api as api


def test_query_solr_returns_docs(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"success": True, "total": 2, "data": [{"url": "u1"}]}
    result = api.query_solr("36034853")
    assert result["numFound"] == 2
    assert result["docs"] == [{"url": "u1"}]


def test_query_solr_throws_on_http_error(mock_get):
    mock_get.return_value.status_code = 500
    mock_get.return_value.text = "boom"
    with pytest.raises(RuntimeError, match="500"):
        api.query_solr("36034853")


def test_query_solr_missing_data_returns_empty(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"success": False}
    result = api.query_solr("36034853")
    assert result["numFound"] == 0
    assert result["docs"] == []


def test_upsert_jobs_keeps_cif(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"success": True, "count": 1}
    api.upsert_jobs([{"url": "u", "cif": "36034853"}])
    sent = mock_post.call_args.kwargs["json"]
    assert sent[0]["cif"] == "36034853"


def test_upsert_jobs_throws_on_http_error(mock_post):
    mock_post.return_value.status_code = 500
    mock_post.return_value.text = "boom"
    with pytest.raises(RuntimeError, match="500"):
        api.upsert_jobs([{"url": "u", "cif": "36034853"}])


def test_upsert_jobs_throws_on_success_false(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"success": False}
    with pytest.raises(RuntimeError, match="upload failed"):
        api.upsert_jobs([{"url": "u", "cif": "36034853"}])


def test_delete_job_by_url(mock_delete):
    mock_delete.return_value.status_code = 200
    mock_delete.return_value.json.return_value = {"success": True}
    api.delete_job_by_url("https://example.com/job")
    assert mock_delete.call_args.kwargs["json"] == {"url": "https://example.com/job"}


def test_delete_job_by_url_404_is_silent(mock_delete):
    mock_delete.return_value.status_code = 404
    api.delete_job_by_url("https://example.com/job")


def test_delete_job_by_url_throws_on_http_error(mock_delete):
    mock_delete.return_value.status_code = 500
    mock_delete.return_value.text = "boom"
    with pytest.raises(RuntimeError, match="500"):
        api.delete_job_by_url("https://example.com/job")


def test_delete_jobs_by_cif_throws_on_success_false(mock_delete):
    mock_delete.return_value.status_code = 200
    mock_delete.return_value.json.return_value = {"success": False}
    with pytest.raises(RuntimeError, match="delete failed"):
        api.delete_jobs_by_cif("36034853")


def test_upsert_company_keeps_id(mock_put):
    mock_put.return_value.status_code = 200
    mock_put.return_value.json.return_value = {"success": True}
    api.upsert_company({"id": "36034853", "company": "EVOLUTION PRODUCTS RO S.R.L."})
    sent = mock_put.call_args.kwargs["json"]
    assert sent["id"] == "36034853"


def test_upsert_company_throws_on_http_error(mock_put):
    mock_put.return_value.status_code = 500
    mock_put.return_value.text = "boom"
    with pytest.raises(RuntimeError, match="500"):
        api.upsert_company({"id": "36034853", "company": "EVOLUTION PRODUCTS RO S.R.L."})


def test_check_url_head(mock_head):
    mock_head.return_value.ok = True
    mock_head.return_value.status_code = 200
    result = api.check_url("https://example.com")
    assert result["valid"] is True


def test_check_url_failure(mock_head):
    mock_head.return_value.ok = False
    mock_head.return_value.status_code = 404
    result = api.check_url("https://example.com")
    assert result["valid"] is False


def test_check_url_redirect_invalid(mock_head):
    mock_head.return_value.ok = True
    mock_head.return_value.status_code = 302
    result = api.check_url("https://example.com")
    assert result["valid"] is False


BOARD = "https://careers.evolution.com/job/"


def test_run_verification_read_only_by_default(monkeypatch, capsys):
    monkeypatch.setattr(api, "query_solr", lambda cif: {
        "numFound": 2,
        "docs": [
            {"url": BOARD + "dead1", "location": [], "workmode": None, "title": "A"},
            {"url": "https://www.ejobs.ro/job/x", "location": [], "workmode": None, "title": "B"},
        ],
    })
    monkeypatch.setattr(api, "check_url", lambda url: {"url": url, "status": 404, "valid": False})
    delete_mock = mock.Mock()
    monkeypatch.setattr(api, "delete_job_by_url", delete_mock)

    api.run_verification("36034853")

    delete_mock.assert_not_called()
    assert "nothing deleted" in capsys.readouterr().out


def test_run_verification_delete_scoped_to_prefix(monkeypatch):
    docs = [
        {"url": BOARD + "dead1", "location": [], "workmode": None, "title": "A"},
        {"url": "https://www.ejobs.ro/job/x", "location": [], "workmode": None, "title": "B"},
        {"url": BOARD + "ok1", "location": [], "workmode": None, "title": "C"},
    ]
    monkeypatch.setattr(api, "query_solr", lambda cif: {"numFound": len(docs), "docs": docs})

    def _check(url):
        valid = url.endswith("ok1")
        return {"url": url, "status": 200 if valid else 404, "valid": valid}

    monkeypatch.setattr(api, "check_url", _check)
    delete_mock = mock.Mock()
    monkeypatch.setattr(api, "delete_job_by_url", delete_mock)

    api.run_verification("36034853", delete=True, prefix=BOARD)

    assert delete_mock.call_count == 1
    assert delete_mock.call_args.args[0] == BOARD + "dead1"


def test_run_verification_delete_requires_prefix(monkeypatch):
    monkeypatch.setattr(api, "query_solr", lambda cif: {
        "numFound": 1,
        "docs": [{"url": BOARD + "dead1", "location": [], "workmode": None, "title": "A"}],
    })
    monkeypatch.setattr(api, "check_url", lambda url: {"url": url, "status": 404, "valid": False})
    delete_mock = mock.Mock()
    monkeypatch.setattr(api, "delete_job_by_url", delete_mock)

    api.run_verification("36034853", delete=True, prefix=None)

    delete_mock.assert_not_called()
