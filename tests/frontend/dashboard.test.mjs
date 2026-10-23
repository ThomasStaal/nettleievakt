import test from "node:test";
import assert from "node:assert/strict";
import { numeric, format, parseTarget, readDashboard, measuredAt, peakLabel } from "../../custom_components/nettleievakt/www/dashboard-model.mjs";

const config = { has_power: true, peak_days: 3, entities: {
  status: "sensor.status", target_kw: "number.target", projected_peak_kw: "sensor.forecast",
  current_hour_kwh: "sensor.energy", remaining_power_kw: "sensor.budget",
  monthly_peak_kw: "sensor.monthly", month_coverage_percent: "sensor.coverage",
} };
function fixture(status = "ok", forecast = "3") {
  return { connected: true, states: {
    "sensor.status": { state: status, attributes: {} },
    "number.target": { state: "5" },
    "sensor.forecast": { state: forecast },
    "sensor.energy": { state: "1.5" },
    "sensor.budget": { state: "7" },
    "sensor.monthly": { state: "4.4", attributes: { top_days: [] } },
    "sensor.coverage": { state: "45" },
  } };
}

test("unknown, blank and non-finite readings never become zero", () => {
  for (const value of [undefined, null, false, "", " ", "unknown", "unavailable", "NaN", Infinity, {}]) {
    assert.equal(numeric(value), null);
  }
  assert.equal(numeric("0"), 0);
  assert.equal(numeric("4.5"), 4.5);
  assert.equal(format(null, "kW"), "Ikke tilgjengelig");
  assert.equal(format(4.5, "kW"), "4,5 kW");
});

test("threshold accepts Norwegian decimals and rejects unsafe or misleading input", () => {
  for (const [input, expected] of [["4,5", 4.5], ["4.5", 4.5], ["100", 100], ["0,1", 0.1], [" 5 ", 5]]) {
    assert.equal(parseTarget(input), expected);
  }
  for (const input of ["", "0", "100.1", "-1", "Infinity", "1e1", "4.55", "4,5.0", "text", null]) {
    assert.equal(parseTarget(input), null);
  }
});

test("exact boundary is a warning, near-boundary is only an early signal", () => {
  assert.equal(readDashboard(fixture("ok", "4.49"), config).tone, "good");
  assert.equal(readDashboard(fixture("ok", "4.5"), config).title, "Nær varselgrensen");
  assert.equal(readDashboard(fixture("ok", "5"), config).tone, "danger");
  assert.equal(readDashboard(fixture("ok", "6.5"), config).tone, "danger");
});

test("incomplete and stale energy override an old forecast", () => {
  for (const status of ["waiting", "incomplete_hour", "stale", "unknown", "unavailable"]) {
    const data = readDashboard(fixture(status), config);
    assert.notEqual(data.tone, "good");
    assert.equal(data.forecast, null);
    assert.equal(data.energy, null);
    assert.equal(data.budget, null);
  }
});

test("disconnection hides cached values rather than presenting them as current", () => {
  const data = readDashboard({ ...fixture(), connected: false }, config);
  assert.equal(data.title, "Mistet forbindelsen");
  for (const key of ["forecast", "energy", "budget", "monthly", "coverage"]) assert.equal(data[key], null);
  assert.deepEqual(data.topDays, []);
});

test("power and target outages cannot produce a reassuring status", () => {
  assert.equal(readDashboard(fixture(), { ...config, has_power: false }).title, "Ingen effektsensor valgt");
  assert.equal(readDashboard(fixture("ok", "unknown"), config).title, "Kan ikke beregne varselet nå");
  const hass = fixture();
  hass.states["number.target"].state = "unavailable";
  assert.notEqual(readDashboard(hass, config).tone, "good");
});

test("renamed and absent entity IDs are supported", () => {
  const hass = fixture();
  hass.states["sensor.custom_name"] = hass.states["sensor.forecast"];
  delete hass.states["sensor.forecast"];
  const renamed = { ...config, entities: { ...config.entities, projected_peak_kw: "sensor.custom_name" } };
  assert.equal(readDashboard(hass, renamed).forecast, 3);
  assert.equal(readDashboard(hass, config).forecast, null);
  assert.equal(readDashboard({}, {}).title, "Venter på målinger");
});

test("only valid observed top days render, and DST duplicate hours retain offsets", () => {
  const day = { date: "2026-10-25", hour: "2026-10-25T02:00:00+02:00", kw: 4.7 };
  const hass = fixture();
  hass.states["sensor.monthly"].attributes.top_days = [day, { ...day, kw: "unknown" }, { ...day, hour: "broken" }];
  assert.deepEqual(readDashboard(hass, config).topDays, [day]);
  assert.match(peakLabel(day).hour, /UTC\+02:00/);
  assert.match(peakLabel({ ...day, hour: "2026-10-25T02:00:00+01:00" }).hour, /UTC\+01:00/);
  assert.equal(measuredAt(null), "Ingen gyldig måling ennå");
});
