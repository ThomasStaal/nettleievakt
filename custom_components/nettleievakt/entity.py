"""Shared local entity metadata."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class NettleievaktEntity(CoordinatorEntity):
    """Group calculated entities without pretending to be a physical meter."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, key):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="Praktiskinfo",
            model="Nettleievakt",
            entry_type=DeviceEntryType.SERVICE,
        )
