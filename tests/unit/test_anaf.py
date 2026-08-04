"""Unit tests for ANAF integration with mocked HTTP."""

from unittest import mock

from scraper import anaf


def test_get_company_from_anaf_cuiscan_first(mock_get):
    mock_get.side_effect = [
        mock.Mock(status_code=200, json=lambda: {
            "denumire": "EVOLUTION PRODUCTS RO S.R.L.", "cui": "36034853",
            "adresa": "CLUJ-NAPOCA", "activ": True}),
    ]
    company = anaf.get_company_from_anaf("36034853")
    assert company["denumire"] == "EVOLUTION PRODUCTS RO S.R.L."
    assert company["stareInregistrare"] == "INREGISTRAT"


def test_get_company_from_anaf_demoanaf_fallback(mock_get):
    mock_get.side_effect = [
        mock.Mock(status_code=500, raise_for_status=mock.Mock(side_effect=Exception("http"))),
        mock.Mock(status_code=200, json=lambda: {
            "denumire": "EVOLUTION PRODUCTS RO S.R.L.", "cif": "36034853",
            "adresa": "CLUJ-NAPOCA", "stareInregistrare": "INREGISTRAT"}),
    ]
    company = anaf.get_company_from_anaf("36034853")
    assert company["denumire"] == "EVOLUTION PRODUCTS RO S.R.L."
    assert company["stareInregistrare"] == "INREGISTRAT"


def test_get_company_from_anaf_skips_payment_error(mock_get):
    mock_get.side_effect = [
        mock.Mock(status_code=200, json=lambda: {"error": "payment_required", "accepts": []}),
        mock.Mock(status_code=200, json=lambda: {
            "denumire": "EVOLUTION PRODUCTS RO S.R.L.", "cui": "36034853",
            "adresa": "CLUJ-NAPOCA", "activ": True}),
    ]
    company = anaf.get_company_from_anaf("36034853")
    assert company["denumire"] == "EVOLUTION PRODUCTS RO S.R.L."


def test_get_company_from_anaf_returns_none_on_total_failure(mock_get):
    mock_get.side_effect = Exception("network")
    assert anaf.get_company_from_anaf("36034853") is None


def test_search_anofm_parses_rows(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"rows": [
        {"id": "1", "occupation": "Inginer", "address_locality_name": "Cluj > Cluj-Napoca"},
        {"id": "2", "occupation": "Electrician", "address_locality_name": "Bucuresti > Bucuresti"},
    ]}
    jobs = anaf.search_anofm("36034853")
    assert len(jobs) == 2
    assert jobs[0]["url"].endswith("/job/1")
    assert jobs[0]["title"] == "Inginer"
    assert jobs[0]["location"] == ["Cluj-Napoca"]


def test_search_anofm_empty_on_error(mock_post):
    mock_post.side_effect = Exception("network")
    assert anaf.search_anofm("36034853") == []


def test_search_anofm_non_200(mock_post):
    mock_post.return_value.status_code = 500
    assert anaf.search_anofm("36034853") == []


def test_validate_and_get_company_falls_back_to_config(monkeypatch, company_config):
    from scraper import company
    monkeypatch.setattr(company, "get_company_data", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no api")))
    result = company.validate_and_get_company()
    assert result["company"] == company_config["company"]
    assert result["cif"] == company_config["id"]
    assert result["status"] == "active"
