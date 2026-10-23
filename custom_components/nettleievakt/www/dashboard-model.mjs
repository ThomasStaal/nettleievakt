const numberFormat = new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 2 });

export function numeric(value) {
  if (typeof value !== "number" && typeof value !== "string") return null;
  if (typeof value === "string" && !value.trim()) return null;
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
}

export function format(value, unit = "") {
  return value === null ? "Ikke tilgjengelig" : `${numberFormat.format(value)}${unit ? ` ${unit}` : ""}`;
}

export function parseTarget(input) {
  if (!/^\d+(?:[.,]\d)?$/.test(String(input).trim())) return null;
  const value = Number(String(input).trim().replace(",", "."));
  return value >= 0.1 && value <= 100 ? value : null;
}

export function readDashboard(hass, config = {}) {
  const entity = (key) => hass?.states?.[config.entities?.[key]];
  const value = (key) => numeric(entity(key)?.state);
  const connected = Boolean(hass) && hass.connected !== false;
  const status = entity("status")?.state;
  const target = value("target_kw");
  const forecast = connected && status === "ok" ? value("projected_peak_kw") : null;
  let tone = "neutral", title, description, icon = "mdi:clock-outline";
  if (!connected) {
    title = "Mistet forbindelsen";
    description = "Dashboardet får ikke kontakt med Home Assistant. Tallene oppdateres ikke.";
    tone = "warning";
    icon = "mdi:wifi-off";
  } else if (status === "stale") {
    title = "Målingene er for gamle";
    description = "Vi mangler ferske målinger. Derfor kan vi ikke vurdere denne timen.";
    tone = "warning";
  } else if (status === "incomplete_hour") {
    title = "Denne timen mangler målinger";
    description = "Vi kjenner ikke hele timens forbruk. En ny beregning starter ved neste hele time, hvis målingene kommer som normalt.";
  } else if (status !== "ok") {
    title = "Venter på målinger";
    description = "Beregningen starter når energimåleren sender gyldige data. Første delvise time kan ikke beregnes.";
  } else if (!config.has_power) {
    title = "Ingen effektsensor valgt";
    description = "Kjøpt strøm måles, men prognose og grensevarsel trenger også en effektsensor.";
  } else if (forecast === null || target === null) {
    title = "Kan ikke beregne varselet nå";
    description = "Prognosen eller varselgrensen mangler. Sjekk at effektsensoren sender ferske målinger.";
  } else if (forecast >= target) {
    title = "Timen ligger an til å nå grensen";
    description = "Hvis forbruket fortsetter som nå, når eller passerer timesnittet varselgrensen. Vurder om noe forbruk kan vente.";
    tone = "danger";
    icon = "mdi:alert-circle-outline";
  } else if (forecast >= target * 0.9) {
    title = "Nær varselgrensen";
    description = "Prognosen er under grensen, men har høyst 10 prosent margin. Dette er et tidlig signal, ikke et utløst grensevarsel.";
    tone = "warning";
    icon = "mdi:alert-outline";
  } else {
    title = "Under varselgrensen";
    description = "Prognosen er under grensen du har valgt. Bildet kan endre seg hvis forbruket øker.";
    tone = "good";
    icon = "mdi:check-circle-outline";
  }
  const monthly = entity("monthly_peak_kw");
  const topDays = (Array.isArray(monthly?.attributes?.top_days) ? monthly.attributes.top_days : [])
    .filter((day) => typeof day.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(day.date)
      && numeric(day.kw) !== null && numeric(day.kw) >= 0
      && Number.isFinite(Date.parse(day.hour)))
    .map((day) => ({ ...day, kw: numeric(day.kw) }));
  return {
    connected, status, target, forecast, tone, title, description, icon,
    energy: connected && status === "ok" ? value("current_hour_kwh") : null,
    budget: connected && status === "ok" ? value("remaining_power_kw") : null,
    monthly: connected ? value("monthly_peak_kw") : null,
    coverage: connected ? value("month_coverage_percent") : null,
    topDays: connected ? topDays : [],
    lastMeasurement: entity("status")?.attributes?.last_measurement,
    peakDays: Number.isInteger(config.peak_days) ? config.peak_days : 3,
  };
}

export function measuredAt(value) {
  const date = new Date(value ?? "");
  if (!Number.isFinite(date.getTime())) return "Ingen gyldig måling ennå";
  return `Siste energimåling: ${new Intl.DateTimeFormat("nb-NO", {
    timeZone: "Europe/Oslo", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).format(date)}`;
}

export function peakLabel(day) {
  const start = new Date(day.hour);
  const end = new Date(start.getTime() + 3600000);
  const clock = new Intl.DateTimeFormat("nb-NO", { timeZone: "Europe/Oslo", hour: "2-digit", minute: "2-digit" });
  const date = new Intl.DateTimeFormat("nb-NO", { timeZone: "Europe/Oslo", day: "numeric", month: "short" }).format(start);
  // The offset distinguishes the repeated clock hour when daylight saving ends.
  const offset = day.hour.match(/([+-]\d{2}:\d{2}|Z)$/)?.[1] ?? "";
  return { date, hour: `${clock.format(start)}–${clock.format(end)} (${offset === "Z" ? "UTC" : `UTC${offset}`})` };
}
