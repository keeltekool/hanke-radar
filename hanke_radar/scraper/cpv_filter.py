"""CPV code filtering and trade tagging."""

from hanke_radar.db.seed import TRADE_CPV_SEEDS

# Build a lookup: cpv_prefix -> list of trade_keys
_PREFIX_TO_TRADES: dict[str, list[str]] = {}
for mapping in TRADE_CPV_SEEDS:
    prefix = mapping["cpv_prefix"]
    trade = mapping["trade_key"]
    _PREFIX_TO_TRADES.setdefault(prefix, []).append(trade)

# All known prefixes we care about (sorted longest first for greedy matching)
_SORTED_PREFIXES = sorted(_PREFIX_TO_TRADES.keys(), key=len, reverse=True)

# Broad CPV divisions that are always trade-relevant (construction, maintenance, engineering)
TRADE_RELEVANT_DIVISIONS = {"45", "50", "71"}


def is_trade_relevant(cpv_code: str) -> bool:
    """Check if a CPV code is relevant to any construction/maintenance/engineering trade.

    Accepts ANY code in CPV divisions 45 (construction), 50 (repair/maintenance),
    or 71 (architectural/engineering services). This is intentionally broad to
    capture the maximum number of relevant procurements.
    """
    if not cpv_code:
        return False
    cpv_clean = cpv_code.strip().split("-")[0].strip()
    return cpv_clean[:2] in TRADE_RELEVANT_DIVISIONS


def get_trade_tags(cpv_codes: list[str]) -> list[str]:
    """Derive trade tags from a list of CPV codes.

    Maps specific CPV prefixes to trades (plumbing, electrical, etc.).
    Any trade-relevant CPV that doesn't match a specific prefix
    gets the 'general' tag as fallback.
    """
    tags: set[str] = set()
    for cpv in cpv_codes:
        if not cpv:
            continue
        cpv_clean = cpv.strip().split("-")[0].strip()
        matched_specific = False
        for prefix in _SORTED_PREFIXES:
            if cpv_clean.startswith(prefix):
                tags.update(_PREFIX_TO_TRADES[prefix])
                matched_specific = True
        # Fallback: if CPV is in a relevant division but has no specific trade mapping
        if not matched_specific and cpv_clean[:2] in TRADE_RELEVANT_DIVISIONS:
            tags.add("general")
    return sorted(tags)
