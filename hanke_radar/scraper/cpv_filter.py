"""CPV code filtering and trade tagging."""

from hanke_radar.db.seed import TRADE_CPV_SEEDS

# Build a lookup: cpv_prefix → list of trade_keys
_PREFIX_TO_TRADES: dict[str, list[str]] = {}
for mapping in TRADE_CPV_SEEDS:
    prefix = mapping["cpv_prefix"]
    trade = mapping["trade_key"]
    _PREFIX_TO_TRADES.setdefault(prefix, []).append(trade)

# All known prefixes we care about (sorted longest first for greedy matching)
_SORTED_PREFIXES = sorted(_PREFIX_TO_TRADES.keys(), key=len, reverse=True)


def is_trade_relevant(cpv_code: str) -> bool:
    """Check if a CPV code is relevant to any tracked trade."""
    if not cpv_code:
        return False
    # Strip spaces, take just the numeric part
    cpv_clean = cpv_code.strip().split("-")[0].strip()
    for prefix in _SORTED_PREFIXES:
        if cpv_clean.startswith(prefix):
            return True
    return False


def get_trade_tags(cpv_codes: list[str]) -> list[str]:
    """Derive trade tags from a list of CPV codes."""
    tags: set[str] = set()
    for cpv in cpv_codes:
        cpv_clean = cpv.strip().split("-")[0].strip()
        for prefix in _SORTED_PREFIXES:
            if cpv_clean.startswith(prefix):
                tags.update(_PREFIX_TO_TRADES[prefix])
    return sorted(tags)
