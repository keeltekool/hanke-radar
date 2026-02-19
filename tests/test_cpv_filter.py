"""Tests for CPV code filtering and trade tagging."""

from hanke_radar.scraper.cpv_filter import get_trade_tags, is_trade_relevant


def test_plumbing_cpv_is_relevant():
    assert is_trade_relevant("45330000") is True


def test_electrical_cpv_is_relevant():
    assert is_trade_relevant("45310000") is True


def test_painting_cpv_is_relevant():
    assert is_trade_relevant("45440000") is True


def test_hvac_cpv_is_relevant():
    assert is_trade_relevant("45331000") is True


def test_general_construction_is_relevant():
    assert is_trade_relevant("45400000") is True


def test_maintenance_is_relevant():
    assert is_trade_relevant("50700000") is True


def test_unrelated_cpv_not_relevant():
    # IT services
    assert is_trade_relevant("72000000") is False


def test_empty_cpv_not_relevant():
    assert is_trade_relevant("") is False
    assert is_trade_relevant(None) is False


def test_get_trade_tags_single():
    tags = get_trade_tags(["45330000"])
    assert "plumbing" in tags


def test_get_trade_tags_multiple():
    tags = get_trade_tags(["45310000", "45330000"])
    assert "electrical" in tags
    assert "plumbing" in tags


def test_get_trade_tags_empty():
    assert get_trade_tags([]) == []


def test_cpv_with_dash_suffix():
    """CPV codes sometimes have a check digit suffix like 45330000-9."""
    assert is_trade_relevant("45330000-9") is True
