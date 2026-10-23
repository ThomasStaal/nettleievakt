"""An hourly warning is not a prediction of the final monthly bill."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .entity import NettleievaktEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([HourlyTargetRisk(entry.runtime_data)])


class HourlyTargetRisk(NettleievaktEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator):
        super().__init__(coordinator, "hourly_target_risk")

    @property
    def is_on(self):
        return self.coordinator.data["hourly_target_risk"]

    @property
    def extra_state_attributes(self):
        return {
            "target_kw": self.coordinator.data["target_kw"],
            "projected_peak_kw": self.coordinator.data["projected_peak_kw"],
        }
