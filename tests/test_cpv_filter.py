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


def test_engineering_services_relevant():
    """CPV division 71 (architectural/engineering) is trade-relevant."""
    assert is_trade_relevant("71300000") is True
    assert is_trade_relevant("71321000") is True


def test_broad_construction_relevant():
    """Any CPV in division 45 should be relevant."""
    assert is_trade_relevant("45000000") is True
    assert is_trade_relevant("45110000") is True
    assert is_trade_relevant("45260000") is True


def test_broad_maintenance_relevant():
    """Any CPV in division 50 should be relevant."""
    assert is_trade_relevant("50000000") is True
    assert is_trade_relevant("50800000") is True


def test_unrelated_cpv_not_relevant():
    # IT services
    assert is_trade_relevant("72000000") is False
    # Medical supplies
    assert is_trade_relevant("33000000") is False
    # Food
    assert is_trade_relevant("15000000") is False


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


def test_get_trade_tags_general_fallback():
    """CPV codes in division 45/50/71 without a specific trade mapping get 'general'."""
    # 71300000 = hydraulic engineering — no specific trade prefix match
    tags = get_trade_tags(["71300000"])
    assert "general" in tags


def test_get_trade_tags_mixed_specific_and_general():
    """Mix of specific and unmatched CPVs produces correct tags."""
    tags = get_trade_tags(["45310000", "71300000"])
    assert "electrical" in tags
    assert "general" in tags


def test_cpv_with_dash_suffix():
    """CPV codes sometimes have a check digit suffix like 45330000-9."""
    assert is_trade_relevant("45330000-9") is True


def test_get_trade_tags_new_seeds():
    """Verify newly added CPV prefix mappings work."""
    # Sewage → plumbing
    tags = get_trade_tags(["45232000"])
    assert "plumbing" in tags

    # Alarm systems → electrical
    tags = get_trade_tags(["45312000"])
    assert "electrical" in tags

    # Facade → painting
    tags = get_trade_tags(["45443000"])
    assert "painting" in tags

    # Central heating repair → hvac
    tags = get_trade_tags(["50720000"])
    assert "hvac" in tags

    # Roof works → general
    tags = get_trade_tags(["45260000"])
    assert "general" in tags

    # Misc repair → maintenance
    tags = get_trade_tags(["50800000"])
    assert "maintenance" in tags
