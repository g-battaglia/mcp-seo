"""Tests for robots.txt analyzer."""

from mcp_seo.analyzers.robots import RobotsRule, _path_matches, is_url_blocked


class TestPathMatching:
    def test_exact_match(self):
        assert _path_matches("/admin", "/admin") is True

    def test_prefix_match(self):
        assert _path_matches("/admin/page", "/admin") is True

    def test_no_match(self):
        assert _path_matches("/public", "/admin") is False

    def test_wildcard(self):
        assert _path_matches("/images/photo.jpg", "/images/*.jpg") is True

    def test_dollar_end(self):
        assert _path_matches("/page.html", "*.html$") is True
        assert _path_matches("/page.html/extra", "*.html$") is False

    def test_root_disallow(self):
        assert _path_matches("/anything", "/") is True

    def test_empty_pattern(self):
        assert _path_matches("/anything", "") is False


class TestIsUrlBlocked:
    def test_blocked_by_wildcard(self):
        rules = [RobotsRule(user_agent="*", disallow=["/admin"])]
        assert is_url_blocked(rules, "https://example.com/admin/page") is True

    def test_not_blocked(self):
        rules = [RobotsRule(user_agent="*", disallow=["/admin"])]
        assert is_url_blocked(rules, "https://example.com/public") is False

    def test_allow_overrides_disallow(self):
        rules = [RobotsRule(user_agent="*", disallow=["/admin"], allow=["/admin/public"])]
        assert is_url_blocked(rules, "https://example.com/admin/public") is False

    def test_bot_specific_rule(self):
        rules = [
            RobotsRule(user_agent="*", disallow=[]),
            RobotsRule(user_agent="Googlebot", disallow=["/private"]),
        ]
        assert is_url_blocked(rules, "https://example.com/private", "Googlebot") is True
        assert is_url_blocked(rules, "https://example.com/private", "*") is False

    def test_no_rules(self):
        assert is_url_blocked([], "https://example.com/anything") is False
