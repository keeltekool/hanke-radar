"""Seed data for trade-CPV mappings."""


def _m(prefix: str, key: str, et: str, en: str) -> dict:
    return {"cpv_prefix": prefix, "trade_key": key, "trade_name_et": et, "trade_name_en": en}


# Confirmed CPV prefixes from real riigihanked.riik.ee notices
TRADE_CPV_SEEDS = [
    # Plumbing
    _m("4533", "plumbing", "Torustik", "Plumbing"),
    _m("45332", "plumbing", "Torustik", "Plumbing"),
    # Electrical
    _m("4531", "electrical", "Elekter", "Electrical"),
    # Painting
    _m("4544", "painting", "Maalimine", "Painting"),
    _m("45442", "painting", "Maalimine", "Painting"),
    # HVAC
    _m("45331", "hvac", "Küte ja ventilatsioon", "HVAC"),
    # General construction / finishing
    _m("4540", "general", "Ehitustööd", "Construction"),
    _m("4543", "general", "Ehitustööd", "Construction"),
    _m("4545", "general", "Ehitustööd", "Construction"),
    _m("4521", "general", "Ehitustööd", "Construction"),
    # Maintenance / repair
    _m("5070", "maintenance", "Hooldus", "Maintenance"),
    _m("5071", "maintenance", "Hooldus", "Maintenance"),
]
