"""Tests for the HTML enricher contact extraction."""

from hanke_radar.scraper.html_enricher import _extract_contact_from_text


def test_extract_email():
    text = "Kontaktisik: Sven Naarits (e-mail: sven.naarits@jarvekyla.edu.ee)"
    result = _extract_contact_from_text(text)
    assert result["contact_email"] == "sven.naarits@jarvekyla.edu.ee"


def test_extract_phone():
    text = "Kontaktisik: Sven Naarits (tel: 5564 0996)"
    result = _extract_contact_from_text(text)
    assert "5564" in result["contact_phone"]


def test_extract_both():
    text = "Sven Naarits (tel: 5564 0996, e-mail: sven.naarits@jarvekyla.edu.ee)"
    result = _extract_contact_from_text(text)
    assert "contact_email" in result
    assert "contact_phone" in result


def test_no_contact_info():
    text = "Hankemenetlus ei ole jaotatud osadeks."
    result = _extract_contact_from_text(text)
    assert result == {}


def test_extract_international_phone():
    text = "Kontakt: +372 5564 0996"
    result = _extract_contact_from_text(text)
    assert "contact_phone" in result
