"""Seed data for trade-CPV mappings."""


def _m(prefix: str, key: str, et: str, en: str) -> dict:
    return {"cpv_prefix": prefix, "trade_key": key, "trade_name_et": et, "trade_name_en": en}


# Comprehensive CPV prefixes covering construction, maintenance, and engineering trades.
# Division 45: Construction work
# Division 50: Repair and maintenance services
# Division 71: Architectural, construction, engineering services
TRADE_CPV_SEEDS = [
    # ── Plumbing / Sanitary ──
    _m("4533", "plumbing", "Torustik", "Plumbing"),
    _m("45332", "plumbing", "Torustik", "Plumbing"),       # Tiling and plumbing
    _m("45232", "plumbing", "Torustik", "Plumbing"),       # Sewage/drainage construction
    _m("45333", "plumbing", "Torustik", "Plumbing"),       # Gas fitting

    # ── Electrical ──
    _m("4531", "electrical", "Elekter", "Electrical"),
    _m("45312", "electrical", "Elekter", "Electrical"),     # Alarm/antenna systems
    _m("45314", "electrical", "Elekter", "Electrical"),     # Telecommunications installations
    _m("45315", "electrical", "Elekter", "Electrical"),     # Electrical heating
    _m("45316", "electrical", "Elekter", "Electrical"),     # Exterior lighting
    _m("50711", "electrical", "Elekter", "Electrical"),     # Electrical equipment repair

    # ── Painting / Surface Finishing ──
    _m("4544", "painting", "Maalimine", "Painting"),
    _m("45442", "painting", "Maalimine", "Painting"),       # Protective coatings
    _m("45443", "painting", "Maalimine", "Painting"),       # Facade work

    # ── HVAC ──
    _m("45331", "hvac", "Küte ja ventilatsioon", "HVAC"),
    _m("45321", "hvac", "Küte ja ventilatsioon", "HVAC"),   # Thermal insulation
    _m("50720", "hvac", "Küte ja ventilatsioon", "HVAC"),   # Central heating repair
    _m("50730", "hvac", "Küte ja ventilatsioon", "HVAC"),   # Cooling groups repair

    # ── General Construction / Finishing ──
    _m("451", "general", "Ehitustööd", "Construction"),     # Site preparation
    _m("4520", "general", "Ehitustööd", "Construction"),    # Complete construction works
    _m("4521", "general", "Ehitustööd", "Construction"),    # Building construction
    _m("4522", "general", "Ehitustööd", "Construction"),    # Engineering works
    _m("4523", "general", "Ehitustööd", "Construction"),    # Pipelines, roads, power lines
    _m("4524", "general", "Ehitustööd", "Construction"),    # Hydraulic works
    _m("4525", "general", "Ehitustööd", "Construction"),    # Factory construction
    _m("4526", "general", "Ehitustööd", "Construction"),    # Roof works / special trade
    _m("45313", "general", "Ehitustööd", "Construction"),   # Lift/escalator installation
    _m("4532", "general", "Ehitustööd", "Construction"),    # Insulation work
    _m("4534", "general", "Ehitustööd", "Construction"),    # Fencing/railing installation
    _m("4535", "general", "Ehitustööd", "Construction"),    # Mechanical installations
    _m("45343", "general", "Ehitustööd", "Construction"),   # Fire prevention installations
    _m("4540", "general", "Ehitustööd", "Construction"),    # Building completion work
    _m("4541", "general", "Ehitustööd", "Construction"),    # Plastering
    _m("4542", "general", "Ehitustööd", "Construction"),    # Joinery and carpentry
    _m("4543", "general", "Ehitustööd", "Construction"),    # Floor and wall covering
    _m("4545", "general", "Ehitustööd", "Construction"),    # Other building completion

    # ── Maintenance / Repair ──
    _m("5070", "maintenance", "Hooldus", "Maintenance"),    # Building installation repair
    _m("5071", "maintenance", "Hooldus", "Maintenance"),    # Electrical/mechanical building
    _m("50712", "maintenance", "Hooldus", "Maintenance"),   # Mechanical equipment repair
    _m("5080", "maintenance", "Hooldus", "Maintenance"),    # Misc repair and maintenance
]
