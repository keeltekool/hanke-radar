"""Seed data for trade-CPV mappings."""

# Confirmed CPV prefixes from real riigihanked.riik.ee notices
TRADE_CPV_SEEDS = [
    # Plumbing
    {"cpv_prefix": "4533", "trade_key": "plumbing", "trade_name_et": "Torustik", "trade_name_en": "Plumbing"},
    {"cpv_prefix": "45332", "trade_key": "plumbing", "trade_name_et": "Torustik", "trade_name_en": "Plumbing"},
    # Electrical
    {"cpv_prefix": "4531", "trade_key": "electrical", "trade_name_et": "Elekter", "trade_name_en": "Electrical"},
    # Painting
    {"cpv_prefix": "4544", "trade_key": "painting", "trade_name_et": "Maalimine", "trade_name_en": "Painting"},
    {"cpv_prefix": "45442", "trade_key": "painting", "trade_name_et": "Maalimine", "trade_name_en": "Painting"},
    # HVAC
    {"cpv_prefix": "45331", "trade_key": "hvac", "trade_name_et": "Küte ja ventilatsioon", "trade_name_en": "HVAC"},
    # General construction / finishing
    {"cpv_prefix": "4540", "trade_key": "general", "trade_name_et": "Ehitustööd", "trade_name_en": "Construction"},
    {"cpv_prefix": "4543", "trade_key": "general", "trade_name_et": "Ehitustööd", "trade_name_en": "Construction"},
    {"cpv_prefix": "4545", "trade_key": "general", "trade_name_et": "Ehitustööd", "trade_name_en": "Construction"},
    {"cpv_prefix": "4521", "trade_key": "general", "trade_name_et": "Ehitustööd", "trade_name_en": "Construction"},
    # Maintenance / repair
    {"cpv_prefix": "5070", "trade_key": "maintenance", "trade_name_et": "Hooldus", "trade_name_en": "Maintenance"},
    {"cpv_prefix": "5071", "trade_key": "maintenance", "trade_name_et": "Hooldus", "trade_name_en": "Maintenance"},
]
