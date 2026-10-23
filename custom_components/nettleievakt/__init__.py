"""Nettleievakt: local peak monitoring using existing Home Assistant sensors."""

from homeassistant.const import Platform
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION
from .coordinator import NettleievaktCoordinator
from .dashboard import Dashboard, async_setup_resources

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NUMBER]


async def async_setup(hass, config):
    await async_setup_resources(hass)
    return True


async def async_setup_entry(hass, entry):
    coordinator = NettleievaktCoordinator(hass, entry)
    await coordinator.async_start()
    entry.runtime_data = coordinator
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        await Dashboard(hass, entry).async_start()
    except Exception:
        await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        await coordinator.async_stop()
        raise
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_stop()
        return True
    return False


async def async_remove_entry(hass, entry):
    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
