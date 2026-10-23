"""Register a local panel without touching the user's Lovelace dashboards."""

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er

from .const import CONF_DAYS, CONF_POWER, DEFAULT_DAYS, DOMAIN, VERSION

STATIC_URL = "/nettleievakt_static"
ENTITY_KEYS = {
    "current_hour_kwh": "sensor",
    "projected_peak_kw": "sensor",
    "remaining_power_kw": "sensor",
    "monthly_peak_kw": "sensor",
    "month_coverage_percent": "sensor",
    "status": "sensor",
    "hourly_target_risk": "binary_sensor",
    "target_kw": "number",
}


async def async_setup_resources(hass):
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "www"), False)]
    )


class Dashboard:
    """One stable sidebar entry per meter; resolve IDs from the real registry."""

    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.path = f"nettleievakt-{entry.entry_id.lower()}"
        self.config = {}

    def _config(self):
        registry = er.async_get(self.hass)
        settings = {**self.entry.data, **self.entry.options}
        return {
            "entry_id": self.entry.entry_id,
            "name": self.entry.title,
            "version": VERSION,
            "peak_days": int(settings.get(CONF_DAYS, DEFAULT_DAYS)),
            "has_power": bool(settings.get(CONF_POWER)),
            "entities": {
                key: registry.async_get_entity_id(domain, DOMAIN, f"{self.entry.entry_id}_{key}")
                for key, domain in ENTITY_KEYS.items()
            },
        }

    async def async_start(self):
        self.config = self._config()
        await panel_custom.async_register_panel(
            self.hass,
            frontend_url_path=self.path,
            webcomponent_name="nettleievakt-panel",
            sidebar_title=self.entry.title,
            sidebar_icon="mdi:transmission-tower",
            module_url=f"{STATIC_URL}/panel.js?v={VERSION}",
            config=self.config,
        )
        self.entry.async_on_unload(
            self.hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, self._registry_changed)
        )
        self.entry.async_on_unload(self.remove)

    def _owns_panel(self):
        panel = self.hass.data.get(frontend.DATA_PANELS, {}).get(self.path)
        return panel and (panel.config or {}).get("entry_id") == self.entry.entry_id

    @callback
    def _registry_changed(self, event):
        ids = {value for value in self.config["entities"].values() if value}
        if not any(event.data.get(key) in ids for key in ("entity_id", "old_entity_id")):
            return
        if not self._owns_panel():
            return
        self.config = self._config()
        panel = self.hass.data[frontend.DATA_PANELS][self.path]
        frontend.async_register_built_in_panel(
            self.hass,
            component_name="custom",
            sidebar_title=self.entry.title,
            sidebar_icon="mdi:transmission-tower",
            frontend_url_path=self.path,
            config={**self.config, "_panel_custom": panel.config["_panel_custom"]},
            update=True,
        )

    @callback
    def remove(self):
        if self._owns_panel():
            frontend.async_remove_panel(self.hass, self.path)
