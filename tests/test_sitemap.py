"""Tests for sitemap _is_stale() function."""

from datetime import datetime, timedelta

from mcp_seo.analyzers.sitemap import _is_stale, _validate_lastmod


class TestIsStale:
    def test_recent_date_not_stale(self):
        recent = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        assert _is_stale(recent, months=12) is False

    def test_old_date_is_stale(self):
        old = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        assert _is_stale(old, months=12) is True

    def test_full_datetime_format(self):
        recent = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S")
        assert _is_stale(recent, months=12) is False

    def test_datetime_with_timezone_z(self):
        recent = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        assert _is_stale(recent, months=12) is False

    def test_datetime_with_timezone_offset(self):
        recent = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"
        assert _is_stale(recent, months=12) is False

    def test_year_only_old(self):
        assert _is_stale("2020", months=12) is True

    def test_year_month_recent(self):
        recent = datetime.now().strftime("%Y-%m")
        assert _is_stale(recent, months=12) is False

    def test_invalid_date_returns_false(self):
        assert _is_stale("not-a-date", months=12) is False

    def test_empty_string_returns_false(self):
        assert _is_stale("", months=12) is False

    def test_custom_months_threshold(self):
        # 3 months old should be stale with 2-month threshold
        date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        assert _is_stale(date, months=2) is True

    def test_custom_months_threshold_not_stale(self):
        # 1 month old should not be stale with 2-month threshold
        date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        assert _is_stale(date, months=2) is False


class TestValidateLastmod:
    def test_valid_date(self):
        assert _validate_lastmod("2024-01-15") is True

    def test_valid_datetime(self):
        assert _validate_lastmod("2024-01-15T10:30:00") is True

    def test_valid_datetime_with_tz(self):
        assert _validate_lastmod("2024-01-15T10:30:00+00:00") is True

    def test_valid_year_month(self):
        assert _validate_lastmod("2024-01") is True

    def test_valid_year(self):
        assert _validate_lastmod("2024") is True

    def test_invalid_format(self):
        assert _validate_lastmod("January 15, 2024") is False

    def test_empty_string(self):
        assert _validate_lastmod("") is False
