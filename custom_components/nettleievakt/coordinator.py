"""Listen to HA sensors. Never connect to a meter or any external endpoint."""

import logging
from datetime import timedelta
from math import isfinite

from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

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
    STORAGE_VERSION,
    energy_kwh,
    power_kw,
)
from .engine import PeakTracker

_LOGGER = logging.getLogger(__name__)


class NettleievaktCoordinator(DataUpdateCoordinator):
    """Refresh calculated entities and persist a bounded set of hourly buckets."""

    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry)
        self.entry = entry
        self.settings = {**entry.data, **entry.options}
        self.tracker = PeakTracker(self.settings.get(CONF_GAP, DEFAULT_GAP) * 60)
        self.store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}", private=True)
        self._last_report = None
        self._unsubscribers = []

    async def async_start(self):
        saved = await self.store.async_load()
        if saved:
            try:
                self.tracker.restore(saved, dt_util.utcnow())
            except (ValueError, TypeError, KeyError):
                _LOGGER.error("Stored Nettleievakt history is invalid; setup aborted")
                raise
        sources = [self.settings[CONF_ENERGY]]
        if self.settings.get(CONF_POWER):
            sources.append(self.settings[CONF_POWER])
        self._unsubscribers.append(
            async_track_state_change_event(self.hass, sources, self._source_changed)
        )
        # last_reported also advances for unchanged values. Reading it here avoids
        # treating a cached value as fresh or processing every meter event twice.
        self._unsubscribers.append(
            async_track_time_interval(self.hass, self._tick, timedelta(seconds=15))
        )
        self._tick(dt_util.utcnow())

    @callback
    def _source_changed(self, event):
        self._tick(dt_util.utcnow())

    @callback
    def _tick(self, now):
        source = self.hass.states.get(self.settings[CONF_ENERGY])
        try:
            if source is None or source.attributes.get("restored"):
                raise ValueError
            value = energy_kwh(source.state, source.attributes.get("unit_of_measurement"))
            if not isfinite(value) or value < 0:
                raise ValueError
            if source.last_reported != self._last_report:
                self._last_report = source.last_reported
                if self.tracker.add(source.last_reported, value):
                    self.store.async_delay_save(self.tracker.dump, 60)
        except (ValueError, TypeError, KeyError):
            self.tracker.break_continuity()
            self._last_report = None
        power = None
        power_at = None
        if power_id := self.settings.get(CONF_POWER):
            state = self.hass.states.get(power_id)
            try:
                if state is None or state.attributes.get("restored"):
                    raise ValueError
                power = power_kw(state.state, state.attributes.get("unit_of_measurement"))
                power_at = state.last_reported
            except (ValueError, KeyError, TypeError):
                pass
        self.async_set_updated_data(
            self.tracker.snapshot(
                now,
                target_kw=self.settings.get(CONF_TARGET, DEFAULT_TARGET),
                peak_days=int(self.settings.get(CONF_DAYS, DEFAULT_DAYS)),
                power_kw=power,
                power_at=power_at,
            )
        )

    async def async_stop(self):
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        await self.store.async_save(self.tracker.dump())
