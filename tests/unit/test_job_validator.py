"""Unit tests for job URL validation primitives."""

from unittest import mock

from scraper.job_validator import DEFAULT_EXPIRED_KEYWORDS, validate_by_content, validate_by_head


def test_validate_by_head_active(mock_head):
    mock_head.return_value.ok = True
    mock_head.return_value.status_code = 200
    result = validate_by_head("https://x/job")
    assert result["status"] == "active"


def test_validate_by_head_expired(mock_head):
    mock_head.return_value.ok = False
    mock_head.return_value.status_code = 404
    result = validate_by_head("https://x/job")
    assert result["status"] == "expired"
    assert result["http_status"] == 404


def test_validate_by_head_redirect_is_expired(mock_head):
    mock_head.return_value.ok = True
    mock_head.return_value.status_code = 302
    result = validate_by_head("https://x/job")
    assert result["status"] == "expired"
    assert result["http_status"] == 302


def test_validate_by_head_error(mock_head):
    mock_head.side_effect = Exception("timeout")
    result = validate_by_head("https://x/job")
    assert result["status"] == "error"


def test_validate_by_content_active(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "<html>We are hiring an engineer.</html>"
    result = validate_by_content("https://x/job")
    assert result["status"] == "active"


def test_validate_by_content_expired_keyword(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "<html>This position is no longer accepting applications.</html>"
    result = validate_by_content("https://x/job")
    assert result["status"] == "expired"


def test_validate_by_content_non_200(mock_get):
    mock_get.return_value.status_code = 404
    mock_get.return_value.ok = False
    result = validate_by_content("https://x/job")
    assert result["status"] == "expired"


def test_validate_by_content_redirect_is_expired(mock_get):
    mock_get.return_value.status_code = 302
    mock_get.return_value.ok = True
    mock_get.return_value.text = "<html>jobs list</html>"
    result = validate_by_content("https://x/job")
    assert result["status"] == "expired"
    assert result["http_status"] == 302


def test_validate_by_content_error(mock_get):
    mock_get.side_effect = Exception("timeout")
    result = validate_by_content("https://x/job")
    assert result["status"] == "error"


def test_default_expired_keywords_non_empty():
    assert len(DEFAULT_EXPIRED_KEYWORDS) > 0
