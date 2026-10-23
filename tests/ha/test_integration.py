"""Configuration, lifecycle and state updates against Home Assistant Core."""

from datetime import timedelta

import pytest
from homeassistant import data_entry_flow
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nettleievakt.const import DOMAIN, energy_kwh, power_kw

ENERGY = "sensor.house_import"
POWER = "sensor.house_power"
ENERGY_ATTR = {
    "unit_of_measurement": "kWh",
    "device_class": "energy",
    "state_class": "total_increasing",
}
POWER_ATTR = {"unit_of_measurement": "W", "device_class": "power", "state_class": "measurement"}
CONFIG = {
    "name": "Nettleievakt",
    "energy_sensor": ENERGY,
    "power_sensor": POWER,
    "target_kw": 5.0,
    "peak_days": 3,
    "max_gap_minutes": 5,
}


def seed(hass):
    hass.states.async_set(ENERGY, "100", ENERGY_ATTR)
    hass.states.async_set(POWER, "8000", POWER_ATTR)


async def setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=CONFIG, unique_id=ENERGY, title="Nettleievakt")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def state_for(hass, entry, key, domain="sensor"):
    entity_id = er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{entry.entry_id}_{key}")
    assert entity_id
    return hass.states.get(entity_id)


async def test_user_flow_and_duplicate(hass):
    seed(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONFIG)
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    duplicate = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=CONFIG
    )
    assert duplicate["reason"] == "already_configured"


async def test_flow_rejects_wrong_units_and_unavailable(hass):
    hass.states.async_set(ENERGY, "unknown", ENERGY_ATTR)
    hass.states.async_set(POWER, "500", {**POWER_ATTR, "unit_of_measurement": "V"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=CONFIG
    )
    assert result["errors"] == {"energy_sensor": "invalid_energy", "power_sensor": "invalid_power"}


async def test_real_entities_forecast_outage_and_unload(hass, freezer, hass_storage):
    freezer.move_to("2026-10-01T08:00:00+00:00")
    seed(hass)
    entry = await setup(hass)
    assert state_for(hass, entry, "status").state == "ok"
    for minute in range(1, 31):
        freezer.tick(timedelta(minutes=1))
        hass.states.async_set(ENERGY, str(100 + minute / 15), ENERGY_ATTR)
        hass.states.async_set(POWER, "8000", POWER_ATTR)
        await hass.async_block_till_done()
    assert float(state_for(hass, entry, "current_hour_kwh").state) == pytest.approx(2)
    assert float(state_for(hass, entry, "projected_peak_kw").state) == pytest.approx(6)
    assert state_for(hass, entry, "hourly_target_risk", "binary_sensor").state == "on"
    hass.states.async_set(ENERGY, "unavailable", ENERGY_ATTR)
    await hass.async_block_till_done()
    assert state_for(hass, entry, "current_hour_kwh").state == "unknown"
    assert state_for(hass, entry, "hourly_target_risk", "binary_sensor").state == "unknown"
    coordinator = entry.runtime_data
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert coordinator._unsubscribers == []
    assert f"{DOMAIN}.{entry.entry_id}" in hass_storage


async def test_unchanged_reports_are_not_mistaken_for_stale_cache(hass, freezer):
    freezer.move_to("2026-10-01T08:00:00+00:00")
    seed(hass)
    entry = await setup(hass)
    for _ in range(6):
        freezer.tick(timedelta(minutes=1))
        hass.states.async_set(ENERGY, "100", ENERGY_ATTR)
        entry.runtime_data._tick(dt_util.utcnow())
    assert state_for(hass, entry, "status").state == "ok"
    assert float(state_for(hass, entry, "current_hour_kwh").state) == 0
    freezer.tick(timedelta(minutes=6))
    entry.runtime_data._tick(dt_util.utcnow())
    assert state_for(hass, entry, "status").state == "stale"


async def test_options_keep_history_and_remove_deletes_storage(hass, freezer, hass_storage):
    freezer.move_to("2026-10-01T08:00:00+00:00")
    seed(hass)
    entry = await setup(hass)
    freezer.tick(timedelta(minutes=1))
    hass.states.async_set(ENERGY, "100.1", ENERGY_ATTR)
    await hass.async_block_till_done()
    old_hours = entry.runtime_data.tracker.dump()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "target_kw": 4.5,
            "peak_days": 3,
            "max_gap_minutes": 5,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.tracker.dump() == old_hours
    assert entry.runtime_data.settings["target_kw"] == 4.5
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert f"{DOMAIN}.{entry.entry_id}" not in hass_storage


@pytest.mark.parametrize("value,unit,expected", [(1000, "Wh", 1), (1, "kWh", 1), (1, "MWh", 1000)])
def test_energy_conversion(value, unit, expected):
    assert energy_kwh(str(value), unit) == expected


def test_power_units_and_export():
    assert power_kw("-2000", "W") == -2
    assert power_kw("3", "kW") == 3
    with pytest.raises(KeyError):
        power_kw("3", "V")
