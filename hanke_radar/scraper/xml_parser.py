"""Parse procurement data from riigihanked.riik.ee bulk XML dumps.

XML format: eForms UBL (EU standard)
Root: <OPEN-DATA> containing <ContractNotice> elements
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from lxml import etree

# XML namespaces used in the eForms UBL format
NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "efac": "http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1",
    "efbc": "http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1",
    "efext": "http://data.europa.eu/p27/eforms-ubl-extensions/1",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
}

# eForms notice subtypes that represent active tenders
# 16 = Contract notice (works), 17 = Contract notice (services/supplies)
ACTIVE_TENDER_SUBTYPES = {"16", "17"}


@dataclass
class ParsedProcurement:
    """A single procurement extracted from XML."""

    notice_id: str = ""
    procurement_id: str = ""
    title: str = ""
    description: str = ""
    contracting_auth: str = ""
    contracting_auth_reg: str = ""
    contract_type: str = ""  # derived from CPV range
    procedure_type: str = ""  # open, oth-single, restricted, etc.
    cpv_primary: str = ""
    cpv_additional: list[str] = field(default_factory=list)
    estimated_value: float | None = None
    currency: str = "EUR"
    nuts_code: str = ""
    submission_deadline: datetime | None = None
    publication_date: datetime | None = None
    duration_months: int | None = None
    notice_subtype: str = ""
    source_url: str = ""


def _text(element: etree._Element | None) -> str:
    """Safely extract text from an XML element."""
    if element is None:
        return ""
    return (element.text or "").strip()


def _parse_date(date_str: str, time_str: str = "") -> datetime | None:
    """Parse eForms date/time strings into a timezone-aware datetime."""
    if not date_str:
        return None
    try:
        if time_str:
            # Format: 2026-01-16+02:00 12:00:00.000+02:00
            combined = f"{date_str.split('+')[0]}T{time_str.split('+')[0].split('.')[0]}"
            # Extract timezone from date string
            tz_part = date_str[10:] if len(date_str) > 10 else "+00:00"
            return datetime.fromisoformat(f"{combined}{tz_part}")
        else:
            # Date only: 2026-01-16+02:00
            return datetime.fromisoformat(date_str)
    except (ValueError, IndexError):
        return None


def parse_notice(notice_el: etree._Element) -> ParsedProcurement:
    """Parse a single <ContractNotice> element into a ParsedProcurement."""
    p = ParsedProcurement()

    # Notice ID (UUID)
    notice_id_el = notice_el.find('.//cbc:ID[@schemeName="notice-id"]', NS)
    p.notice_id = _text(notice_id_el)

    # Procurement folder ID
    folder_id_el = notice_el.find(".//cbc:ContractFolderID", NS)
    p.procurement_id = _text(folder_id_el)

    # Notice subtype
    subtype_el = notice_el.find(".//efac:NoticeSubType/cbc:SubTypeCode", NS)
    p.notice_subtype = _text(subtype_el)

    # Title — from first ProcurementProject
    title_el = notice_el.find(".//cac:ProcurementProject/cbc:Name", NS)
    p.title = _text(title_el)

    # Description
    desc_el = notice_el.find(".//cac:ProcurementProject/cbc:Description", NS)
    p.description = _text(desc_el)

    # CPV codes — collect all unique ItemClassificationCode values
    cpv_elements = notice_el.findall(".//cbc:ItemClassificationCode", NS)
    seen_cpvs: list[str] = []
    for cpv_el in cpv_elements:
        code = _text(cpv_el)
        if code and code not in seen_cpvs:
            seen_cpvs.append(code)
    if seen_cpvs:
        p.cpv_primary = seen_cpvs[0]
        p.cpv_additional = seen_cpvs[1:]

    # Procedure type
    proc_code_el = notice_el.find(".//cbc:ProcedureCode", NS)
    p.procedure_type = _text(proc_code_el)

    # Contracting authority — first organization (buyer)
    first_org = notice_el.find(".//efac:Organization/efac:Company", NS)
    if first_org is not None:
        org_name_el = first_org.find(".//cac:PartyName/cbc:Name", NS)
        p.contracting_auth = _text(org_name_el)
        reg_el = first_org.find(".//cac:PartyLegalEntity/cbc:CompanyID", NS)
        p.contracting_auth_reg = _text(reg_el)

    # NUTS code — from ProcurementProject address
    nuts_el = notice_el.find(
        ".//cac:ProcurementProject//cbc:CountrySubentityCode[@listName='nuts']", NS
    )
    if nuts_el is None:
        # Fallback: any NUTS code in the document
        nuts_el = notice_el.find(".//cbc:CountrySubentityCode", NS)
    p.nuts_code = _text(nuts_el)

    # Estimated value
    amount_el = notice_el.find(".//cbc:EstimatedOverallContractAmount", NS)
    if amount_el is not None and amount_el.text:
        try:
            p.estimated_value = float(amount_el.text)
            p.currency = amount_el.get("currencyID", "EUR")
        except ValueError:
            pass

    # Submission deadline
    deadline_period = notice_el.find(".//cac:TenderSubmissionDeadlinePeriod", NS)
    if deadline_period is not None:
        end_date = _text(deadline_period.find("cbc:EndDate", NS))
        end_time = _text(deadline_period.find("cbc:EndTime", NS))
        p.submission_deadline = _parse_date(end_date, end_time)

    # Publication date
    issue_date_el = notice_el.find(".//cbc:IssueDate", NS)
    p.publication_date = _parse_date(_text(issue_date_el))

    # Duration — from PlannedPeriod
    duration_el = notice_el.find(".//cac:PlannedPeriod/cbc:DurationMeasure", NS)
    if duration_el is not None and duration_el.text:
        try:
            p.duration_months = int(float(duration_el.text))
        except ValueError:
            pass

    # Source URL
    if p.procurement_id:
        p.source_url = (
            f"https://riigihanked.riik.ee/rhr-web/#/procurement/{p.procurement_id}/general-info"
        )

    return p


def parse_bulk_xml(xml_content: bytes) -> list[ParsedProcurement]:
    """Parse a full month's bulk XML dump and return all notices.

    Uses full in-memory parsing (lxml). A typical month is ~36MB / ~950 notices,
    which is fine for memory. Returns ALL notices, not just trade-relevant ones
    — filtering is done by the caller.
    """
    root = etree.fromstring(xml_content)
    results = []

    for child in root:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "ContractNotice":
            parsed = parse_notice(child)
            if parsed.notice_id:
                results.append(parsed)

    return results


def is_active_tender(procurement: ParsedProcurement) -> bool:
    """Check if a procurement is an active tender (not a result/modification)."""
    return procurement.notice_subtype in ACTIVE_TENDER_SUBTYPES
