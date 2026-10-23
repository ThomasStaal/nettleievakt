"""UI configuration for the local, sensor-based helper."""

import math

import probatio as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DAYS,
    CONF_ENERGY,
    CONF_GAP,
    CONF_POWER,
    CONF_TARGET,
    DEFAULT_DAYS,
    DEFAULT_GAP,
    DEFAULT_TARGET,
    DOMAIN,
    energy_kwh,
    power_kw,
)


def settings_schema(defaults: dict) -> vol.Schema:
    """Keep tariff assumptions explicit rather than embedding provider prices."""
    return vol.Schema(
        {
            vol.Required(
                CONF_TARGET, default=defaults.get(CONF_TARGET, DEFAULT_TARGET)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1, max=100, step=0.1, unit_of_measurement="kW", mode="box"
                )
            ),
            vol.Required(
                CONF_DAYS, default=defaults.get(CONF_DAYS, DEFAULT_DAYS)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=5, step=1, mode="box")
            ),
            vol.Required(
                CONF_GAP, default=defaults.get(CONF_GAP, DEFAULT_GAP)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=15, step=1, unit_of_measurement="min", mode="box"
                )
            ),
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one grid-import source per entry."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            energy = self.hass.states.get(user_input[CONF_ENERGY])
            try:
                if energy is None:
                    raise ValueError
                value = energy_kwh(energy.state, energy.attributes.get("unit_of_measurement"))
                if (
                    not math.isfinite(value)
                    or value < 0
                    or energy.attributes.get("state_class") not in ("total", "total_increasing")
                    or energy.attributes.get("restored")
                ):
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                errors[CONF_ENERGY] = "invalid_energy"
            power_id = user_input.get(CONF_POWER)
            if power_id:
                power = self.hass.states.get(power_id)
                try:
                    if power is None:
                        raise ValueError
                    value = power_kw(power.state, power.attributes.get("unit_of_measurement"))
                    if not math.isfinite(value) or power.attributes.get("restored"):
                        raise ValueError
                except (ValueError, KeyError, TypeError):
                    errors[CONF_POWER] = "invalid_power"
            if not errors:
                await self.async_set_unique_id(user_input[CONF_ENERGY])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input["name"], data=user_input)
        schema = vol.Schema(
            {
                vol.Required("name", default="Nettleievakt"): selector.TextSelector(),
                vol.Required(CONF_ENERGY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="energy")
                ),
                vol.Optional(CONF_POWER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="power")
                ),
            }
        ).extend(settings_schema(user_input or {}).schema)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    """Allow threshold and tariff-model changes without deleting history."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        values = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=settings_schema(values))
