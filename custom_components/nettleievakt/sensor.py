"""Calculated sensors. None means unknown, never a fabricated zero."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfEnergy, UnitOfPower

from .entity import NettleievaktEntity

DESCRIPTIONS = (
    SensorEntityDescription(
        key="current_hour_kwh",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
    ),
    SensorEntityDescription(
        key="projected_peak_kw",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="remaining_power_kw",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="monthly_peak_kw",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="month_coverage_percent",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="status",
        device_class=SensorDeviceClass.ENUM,
        options=["waiting", "stale", "incomplete_hour", "ok"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(NettleievaktSensor(entry.runtime_data, desc) for desc in DESCRIPTIONS)


class NettleievaktSensor(NettleievaktEntity, SensorEntity):
    def __init__(self, coordinator, description):
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.coordinator.data[self.entity_description.key]

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if self.entity_description.key == "monthly_peak_kw":
            return {
                "top_days": data["top_days"],
                "days_observed": data["days_observed"],
                "month": data["month"],
                "month_coverage_percent": round(data["month_coverage_percent"], 2),
                "provisional": True,
            }
        if self.entity_description.key == "status":
            return {
                "last_measurement": data["last_measurement"],
                "complete_hours": data["complete_hours"],
            }
        if self.entity_description.key in ("projected_peak_kw", "remaining_power_kw"):
            return {"target_kw": data["target_kw"], "last_measurement": data["last_measurement"]}
        return None
