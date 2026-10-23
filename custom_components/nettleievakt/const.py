"""Constants for Nettleievakt."""

DOMAIN = "nettleievakt"
VERSION = "0.2.0b1"
CONF_ENERGY = "energy_sensor"
CONF_POWER = "power_sensor"
CONF_TARGET = "target_kw"
CONF_DAYS = "peak_days"
CONF_GAP = "max_gap_minutes"
DEFAULT_TARGET = 5.0
DEFAULT_DAYS = 3
DEFAULT_GAP = 5
STORAGE_VERSION = 1


def energy_kwh(value: str, unit: str | None) -> float:
    """Convert cumulative grid import to kWh, rejecting unknown units."""
    return float(value) * {"Wh": 0.001, "kWh": 1.0, "MWh": 1000.0}[unit]


def power_kw(value: str, unit: str | None) -> float:
    """Convert instantaneous power to kW; negative values mean export."""
    return float(value) * {"W": 0.001, "kW": 1.0}[unit]
