"""Tests for XML procurement parser."""

from hanke_radar.scraper.xml_parser import (
    ParsedProcurement,
    is_active_tender,
    parse_bulk_xml,
)

# Minimal eForms XML for a single contract notice
SAMPLE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<OPEN-DATA>
<ContractNotice
    xmlns="urn:oasis:names:specification:ubl:schema:xsd:ContractNotice-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:efac="http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1"
    xmlns:efbc="http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1"
    xmlns:efext="http://data.europa.eu/p27/eforms-ubl-extensions/1"
    xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">
  <cbc:ID schemeName="notice-id">test-notice-001</cbc:ID>
  <cbc:ContractFolderID>test-folder-001</cbc:ContractFolderID>
  <cbc:IssueDate>2026-02-01+02:00</cbc:IssueDate>
  <ext:UBLExtensions>
    <ext:UBLExtension>
      <ext:ExtensionContent>
        <efext:EformsExtension>
          <efac:NoticeSubType>
            <cbc:SubTypeCode>16</cbc:SubTypeCode>
          </efac:NoticeSubType>
          <efac:Organizations>
            <efac:Organization>
              <efac:Company>
                <cac:PartyName>
                  <cbc:Name>Tallinna Linnavalitsus</cbc:Name>
                </cac:PartyName>
                <cac:PartyLegalEntity>
                  <cbc:CompanyID>75104221</cbc:CompanyID>
                </cac:PartyLegalEntity>
              </efac:Company>
            </efac:Organization>
          </efac:Organizations>
        </efext:EformsExtension>
      </ext:ExtensionContent>
    </ext:UBLExtension>
  </ext:UBLExtensions>
  <cbc:ProcedureCode>open</cbc:ProcedureCode>
  <cac:ProcurementProject>
    <cbc:Name>Kooli renoveerimise ehitustood</cbc:Name>
    <cbc:Description>Kooli hoone renoveerimise ehitustood</cbc:Description>
    <cac:MainCommodityClassification>
      <cbc:ItemClassificationCode>45210000</cbc:ItemClassificationCode>
    </cac:MainCommodityClassification>
  </cac:ProcurementProject>
  <cac:ProcurementProjectLot>
    <cac:TenderingTerms>
      <cac:TenderSubmissionDeadlinePeriod>
        <cbc:EndDate>2026-03-15+02:00</cbc:EndDate>
        <cbc:EndTime>12:00:00.000+02:00</cbc:EndTime>
      </cac:TenderSubmissionDeadlinePeriod>
      <cac:CallForTendersDocumentReference>
        <cbc:ID>12345678</cbc:ID>
        <cac:Attachment>
          <cac:ExternalReference>
            <cbc:URI>https://riigihanked.riik.ee/rhr-web/#/procurement/9999999/documents?group=B</cbc:URI>
          </cac:ExternalReference>
        </cac:Attachment>
      </cac:CallForTendersDocumentReference>
    </cac:TenderingTerms>
  </cac:ProcurementProjectLot>
</ContractNotice>
</OPEN-DATA>"""


def test_parse_bulk_xml():
    notices = parse_bulk_xml(SAMPLE_XML)
    assert len(notices) == 1


def test_parse_notice_fields():
    notices = parse_bulk_xml(SAMPLE_XML)
    p = notices[0]
    assert p.notice_id == "test-notice-001"
    assert p.procurement_id == "test-folder-001"
    assert p.title == "Kooli renoveerimise ehitustood"
    assert p.description == "Kooli hoone renoveerimise ehitustood"
    assert p.contracting_auth == "Tallinna Linnavalitsus"
    assert p.contracting_auth_reg == "75104221"
    assert p.procedure_type == "open"
    assert p.cpv_primary == "45210000"
    assert p.notice_subtype == "16"


def test_parse_rhr_id_from_uri():
    notices = parse_bulk_xml(SAMPLE_XML)
    p = notices[0]
    assert p.rhr_id == "9999999"


def test_source_url_uses_rhr_id():
    notices = parse_bulk_xml(SAMPLE_XML)
    p = notices[0]
    assert "9999999" in p.source_url
    assert "rhr-web" in p.source_url


def test_parse_deadline():
    notices = parse_bulk_xml(SAMPLE_XML)
    p = notices[0]
    assert p.submission_deadline is not None
    assert p.submission_deadline.year == 2026
    assert p.submission_deadline.month == 3
    assert p.submission_deadline.day == 15


def test_is_active_tender():
    # Above-threshold contract notices
    assert is_active_tender(ParsedProcurement(notice_subtype="16")) is True
    assert is_active_tender(ParsedProcurement(notice_subtype="17")) is True

    # Below-threshold and light regime
    assert is_active_tender(ParsedProcurement(notice_subtype="7")) is True
    assert is_active_tender(ParsedProcurement(notice_subtype="10")) is True

    # Utilities and defence
    assert is_active_tender(ParsedProcurement(notice_subtype="18")) is True
    assert is_active_tender(ParsedProcurement(notice_subtype="20")) is True

    # PIN call-for-competition
    assert is_active_tender(ParsedProcurement(notice_subtype="2")) is True
    assert is_active_tender(ParsedProcurement(notice_subtype="4")) is True


def test_is_not_active_tender():
    # Result/award notice
    assert is_active_tender(ParsedProcurement(notice_subtype="29")) is False
    assert is_active_tender(ParsedProcurement(notice_subtype="25")) is False

    # Planning notice (not CfC)
    assert is_active_tender(ParsedProcurement(notice_subtype="1")) is False

    # Empty
    assert is_active_tender(ParsedProcurement(notice_subtype="")) is False
