import tests.conftest  # noqa: F401  (sys.path setup)
import unittest.mock as mock

import pytest

import scraper.deduplicate as dedupe


HEX_ID = "44136fbed46858e2c9b7025bd25d53f8"


def _doc(url, title="Shuffler"):
    return {"url": url, "title": title, "cif": "", "company": "EVOLUTION GAMING"}


def _resp(url, location=None):
    res = mock.Mock()
    res.url = url
    res.headers = {"Location": location}
    return res


# ---------------------------------------------------------------------------
# search_jobs
# ---------------------------------------------------------------------------

def test_search_jobs_paginates(monkeypatch):
    page1 = {"response": {"docs": [{"url": "u1"}], "numFound": 3}}
    page2 = {"response": {"docs": [{"url": "u2"}, {"url": "u3"}], "numFound": 3}}
    pages = iter([page1, page2])
    fake = mock.Mock(side_effect=lambda *a, **k: _json_resp(next(pages)))
    monkeypatch.setattr(dedupe.requests, "get", fake)

    docs = dedupe.search_jobs("EVOLUTION GAMING", rows=2)

    assert len(docs) == 3
    assert fake.call_count == 2


def test_search_jobs_raises_on_http_error(monkeypatch):
    fake = mock.Mock(return_value=_http_resp(500))
    monkeypatch.setattr(dedupe.requests, "get", fake)
    with pytest.raises(RuntimeError, match="500"):
        dedupe.search_jobs("X")


# ---------------------------------------------------------------------------
# resolve_key
# ---------------------------------------------------------------------------

def test_resolve_key_careerjet(monkeypatch):
    session = mock.Mock()
    location = f"https://www.careerjet.ro/clk/{HEX_ID}.html?affid=abc&psk=def"
    session.head.return_value = _resp(location, location=location)
    monkeypatch.setattr(dedupe, "_session", lambda: session)

    key, kind, final = dedupe.resolve_key("https://jobviewtrack.com/v2/xyz")

    assert key == f"careerjet:{HEX_ID}"
    assert kind == "careerjet"
    assert final.startswith("https://www.careerjet.ro/clk/")


def test_resolve_key_direct(monkeypatch):
    url = "https://careers.evolution.com/job/1/"
    session = mock.Mock()
    session.head.return_value = _resp(url, location=None)
    monkeypatch.setattr(dedupe, "_session", lambda: session)

    key, kind, final = dedupe.resolve_key(url)

    assert key == url.rstrip("/")
    assert kind == "direct"


def test_resolve_key_retries_on_429(monkeypatch):
    rate_limited = _resp("", location=None)
    rate_limited.status_code = 429
    ok = _resp("", location=f"https://www.careerjet.ro/clk/{HEX_ID}.html")
    ok.status_code = 200
    session = mock.Mock()
    session.head.side_effect = [rate_limited, ok]
    monkeypatch.setattr(dedupe, "_session", lambda: session)

    key, kind, final = dedupe.resolve_key("https://jobviewtrack.com/v2/xyz")

    assert key == f"careerjet:{HEX_ID}"
    assert kind == "careerjet"


def test_resolve_key_error(monkeypatch):
    session = mock.Mock()
    session.head.side_effect = TimeoutError("slow")
    monkeypatch.setattr(dedupe, "_session", lambda: session)

    key, kind, final = dedupe.resolve_key("https://jobviewtrack.com/v2/xyz")

    assert kind == "unresolved"
    assert key == "https://jobviewtrack.com/v2/xyz"


# ---------------------------------------------------------------------------
# find_duplicates / pick_keeper
# ---------------------------------------------------------------------------

def test_find_duplicates_groups_by_final_url(monkeypatch):
    docs = [_doc("https://jvt.com/a"), _doc("https://jvt.com/b"), _doc("https://jvt.com/c")]
    keys = [("careerjet:aaa", "careerjet", f"https://www.careerjet.ro/jobad/ro{'a' * 24}"),
            ("careerjet:aaa", "careerjet", f"https://www.careerjet.ro/jobad/ro{'a' * 24}"),
            ("careerjet:bbb", "careerjet", f"https://www.careerjet.ro/jobad/ro{'b' * 24}")]
    monkeypatch.setattr(dedupe, "resolve_key", mock.Mock(side_effect=keys))

    groups = dedupe.find_duplicates(docs, workers=2)

    assert len(groups) == 1
    assert groups[0]["keeper"] == docs[0]
    assert groups[0]["duplicates"] == [docs[1]]


def test_find_duplicates_ignores_uniques(monkeypatch):
    docs = [_doc("https://careers.evolution.com/job/1/"), _doc("https://careers.evolution.com/job/2/")]
    monkeypatch.setattr(dedupe, "resolve_key", mock.Mock(side_effect=[
        ("careers.evolution.com/job/1", "direct", "https://careers.evolution.com/job/1/"),
        ("careers.evolution.com/job/2", "direct", "https://careers.evolution.com/job/2/"),
    ]))
    groups = dedupe.find_duplicates(docs, workers=1)
    assert groups == []


def test_pick_keeper_prefers_board_prefix():
    docs = [_doc("https://jobviewtrack.com/v2/x"), _doc("https://careers.evolution.com/job/1/")]
    keeper = dedupe.pick_keeper(docs)
    assert keeper["url"] == "https://careers.evolution.com/job/1/"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def test_main_dry_run_does_not_mutate(monkeypatch, capsys):
    docs = [_doc("https://jvt.com/a"), _doc("https://jvt.com/b")]
    monkeypatch.setattr(dedupe, "search_jobs", mock.Mock(return_value=docs))
    monkeypatch.setattr(dedupe, "find_duplicates", mock.Mock(return_value=[
        {"key": "careerjet:aaa", "final_url": "https://www.careerjet.ro/jobad/ro" + "a" * 24,
         "keeper": docs[0], "duplicates": [docs[1]], "members": docs}]))
    delete_mock = mock.Mock()
    upsert_mock = mock.Mock()
    monkeypatch.setattr(dedupe, "delete_job_by_url", delete_mock)
    monkeypatch.setattr(dedupe, "upsert_jobs", upsert_mock)

    assert dedupe.main(["EVOLUTION GAMING", "--dry-run"]) == 0

    delete_mock.assert_not_called()
    upsert_mock.assert_not_called()
    assert "Dry run" in capsys.readouterr().out


def test_main_delete_attribues_keeper(monkeypatch):
    docs = [_doc("https://jvt.com/a"), _doc("https://jvt.com/b")]
    group = {"key": "careerjet:aaa", "final_url": "https://www.careerjet.ro/jobad/ro" + "a" * 24,
             "keeper": docs[0], "duplicates": [docs[1]], "members": docs}
    monkeypatch.setattr(dedupe, "search_jobs", mock.Mock(return_value=docs))
    monkeypatch.setattr(dedupe, "find_duplicates", mock.Mock(return_value=[group]))
    delete_mock = mock.Mock()
    upsert_mock = mock.Mock()
    monkeypatch.setattr(dedupe, "delete_job_by_url", delete_mock)
    monkeypatch.setattr(dedupe, "upsert_jobs", upsert_mock)

    assert dedupe.main(["EVOLUTION GAMING", "--delete"]) == 0

    delete_mock.assert_called_once_with("https://jvt.com/b")
    upsert_mock.assert_called_once()
    kept = upsert_mock.call_args.args[0][0]
    assert kept["cif"] == "36034853"
    assert kept["company"] == "EVOLUTION PRODUCTS RO S.R.L."


def test_main_delete_keep_url_pinned(monkeypatch):
    docs = [_doc("https://jvt.com/a"), _doc("https://jvt.com/b")]
    group = {"key": "careerjet:aaa", "final_url": "https://www.careerjet.ro/jobad/ro" + "a" * 24,
             "keeper": docs[0], "duplicates": [docs[1]], "members": docs}
    monkeypatch.setattr(dedupe, "search_jobs", mock.Mock(return_value=docs))
    monkeypatch.setattr(dedupe, "find_duplicates", mock.Mock(return_value=[group]))
    delete_mock = mock.Mock()
    upsert_mock = mock.Mock()
    monkeypatch.setattr(dedupe, "delete_job_by_url", delete_mock)
    monkeypatch.setattr(dedupe, "upsert_jobs", upsert_mock)

    assert dedupe.main(["EVOLUTION GAMING", "--delete", "--keep-url", "https://jvt.com/b"]) == 0

    delete_mock.assert_called_once_with("https://jvt.com/a")
    upsert_mock.assert_called_once()
    kept = upsert_mock.call_args.args[0][0]
    assert kept["url"] == "https://jvt.com/b"


def test_main_delete_keep_url_outside_group_deletes_all(monkeypatch, capsys):
    docs = [_doc("https://jvt.com/a"), _doc("https://jvt.com/b")]
    group = {"key": "careerjet:aaa", "final_url": "https://www.careerjet.ro/jobad/ro" + "a" * 24,
             "keeper": docs[0], "duplicates": [docs[1]], "members": docs}
    monkeypatch.setattr(dedupe, "search_jobs", mock.Mock(return_value=docs))
    monkeypatch.setattr(dedupe, "find_duplicates", mock.Mock(return_value=[group]))
    delete_mock = mock.Mock()
    upsert_mock = mock.Mock()
    monkeypatch.setattr(dedupe, "delete_job_by_url", delete_mock)
    monkeypatch.setattr(dedupe, "upsert_jobs", upsert_mock)

    assert dedupe.main(["EVOLUTION GAMING", "--delete", "--keep-url", "https://already-kept.example/job"]) == 0

    assert delete_mock.call_count == 2
    upsert_mock.assert_not_called()
    assert "already re-attributed" in capsys.readouterr().out


def test_main_wipe_dry_run(monkeypatch, capsys):
    docs = [_doc("https://jvt.com/a"), _doc("https://jvt.com/b")]
    monkeypatch.setattr(dedupe, "search_jobs", mock.Mock(return_value=docs))
    delete_mock = mock.Mock()
    upsert_mock = mock.Mock()
    monkeypatch.setattr(dedupe, "delete_job_by_url", delete_mock)
    monkeypatch.setattr(dedupe, "upsert_jobs", upsert_mock)

    assert dedupe.main(["EVOLUTION GAMING", "--wipe", "--dry-run"]) == 0
    delete_mock.assert_not_called()
    upsert_mock.assert_not_called()
    assert "Wiping ALL 2 listing(s)" in capsys.readouterr().out


def test_main_wipe_delete_deletes_all(monkeypatch, capsys):
    docs = [_doc("https://jvt.com/a"), _doc("https://jvt.com/b")]
    monkeypatch.setattr(dedupe, "search_jobs", mock.Mock(return_value=docs))
    delete_mock = mock.Mock()
    upsert_mock = mock.Mock()
    monkeypatch.setattr(dedupe, "delete_job_by_url", delete_mock)
    monkeypatch.setattr(dedupe, "upsert_jobs", upsert_mock)

    assert dedupe.main(["EVOLUTION GAMING", "--wipe", "--delete"]) == 0
    assert delete_mock.call_count == 2
    upsert_mock.assert_not_called()
    assert "Deleted 2 listing(s)" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _json_resp(payload):
    res = mock.Mock()
    res.status_code = 200
    res.text = ""
    res.json.return_value = payload
    return res


def _http_resp(status):
    res = mock.Mock()
    res.status_code = status
    res.text = "boom"
    return res
