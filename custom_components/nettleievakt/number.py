"""A persistent warning threshold, not a control for electrical equipment."""

import math

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfPower
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_TARGET, DEFAULT_TARGET
from .entity import NettleievaktEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([WarningThreshold(entry.runtime_data)])


class WarningThreshold(NettleievaktEntity, NumberEntity):
    _attr_native_min_value = 0.1
    _attr_native_max_value = 100.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:transmission-tower"

    def __init__(self, coordinator):
        super().__init__(coordinator, CONF_TARGET)

    @property
    def native_value(self):
        return self.coordinator.settings.get(CONF_TARGET, DEFAULT_TARGET)

    async def async_set_native_value(self, value):
        if (
            not math.isfinite(value)
            or not 0.1 <= value <= 100
            or not math.isclose(value * 10, round(value * 10))
        ):
            raise HomeAssistantError("Velg en grense fra 0,1 til 100 kW med maks én desimal.")
        entry = self.coordinator.entry
        self.hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_TARGET: value}
        )
