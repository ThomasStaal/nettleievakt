import { readDashboard, format, measuredAt, parseTarget, peakLabel } from "./dashboard-model.mjs?v=0.2.0b1";

class NettleievaktPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._dirty = false;
    this._saving = false;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; height:100%; overflow:auto; color:var(--primary-text-color,#202725); background:var(--primary-background-color,#f7f8fa); font:15px/1.55 var(--paper-font-body1_-_font-family,system-ui,sans-serif); letter-spacing:0; }
        * { box-sizing:border-box; } [hidden] { display:none!important; }
        h1,h2,p { margin:0; } h1 { font-size:19px; line-height:1.25; } h2 { font-size:18px; line-height:1.35; }
        button,input,a { font:inherit; } button { cursor:pointer; } button:disabled { cursor:default; opacity:.6; }
        button:focus-visible,a:focus-visible,input:focus-visible { outline:3px solid var(--primary-color,#007b83); outline-offset:3px; }
        ha-icon { --mdc-icon-size:22px; flex:none; }
        .header { display:flex; align-items:center; gap:12px; padding:12px 20px; border-bottom:1px solid var(--divider-color,#d4dcda); background:var(--card-background-color,#fff); min-height:65px; }
        .icon-button { display:inline-flex; align-items:center; justify-content:center; width:44px; height:44px; padding:0; color:inherit; background:transparent; border:0; border-radius:6px; }
        .beta { font-size:12px; border:1px solid var(--divider-color,#d4dcda); border-radius:4px; padding:2px 7px; margin-left:auto; white-space:nowrap; }
        main { max-width:1060px; padding:28px; margin:auto; }
        .intro { display:flex; justify-content:space-between; gap:12px; align-items:baseline; margin-bottom:20px; flex-wrap:wrap; }
        .muted,small { color:var(--secondary-text-color,#5a6563); } small { font-size:13px; }
        .status { display:flex; align-items:flex-start; gap:12px; padding:18px 0; border-top:3px solid var(--status-color); border-bottom:1px solid var(--divider-color,#d4dcda); margin-bottom:26px; }
        .status ha-icon { color:var(--status-color); margin-top:2px; }
        .status h2 { margin-bottom:5px; } .status p { max-width:72ch; }
        [data-tone="neutral"] { --status-color:var(--secondary-text-color,#5a6563); }
        [data-tone="good"] { --status-color:var(--success-color,#28744c); }
        [data-tone="warning"] { --status-color:var(--warning-color,#9a6305); }
        [data-tone="danger"] { --status-color:var(--error-color,#bf3737); }
        .hour { display:grid; grid-template-columns:minmax(0,1.2fr) minmax(260px,1fr); gap:32px; }
        .eyebrow { font-size:14px; color:var(--secondary-text-color,#5a6563); }
        .reading { font-size:42px; font-weight:700; line-height:1.2; margin:8px 0; overflow-wrap:anywhere; }
        .reading.missing { font-size:24px; padding:10px 0; }
        .track { height:14px; border-radius:3px; background:var(--divider-color,#dbe1df); overflow:hidden; margin:20px 0 8px; }
        .track-fill { height:100%; width:0; background:var(--status-color); transition:width .2s; }
        .bar-labels { display:flex; justify-content:space-between; gap:8px; font-size:13px; }
        .threshold { padding:22px; border:1px solid var(--divider-color,#cbd7d2); border-radius:8px; background:var(--card-background-color,#fff); }
        .threshold label { display:block; font-weight:650; margin-bottom:8px; }
        .input-row { display:flex; gap:8px; align-items:stretch; margin:12px 0 10px; }
        .number-wrap { display:flex; align-items:center; gap:8px; border:1px solid var(--secondary-text-color,#5a6563); border-radius:5px; padding-right:12px; min-width:0; flex:1; }
        input { width:100%; min-width:0; border:0; padding:10px 12px; background:transparent; color:inherit; font-weight:650; font-size:20px; border-radius:5px; }
        .save { display:inline-flex; align-items:center; justify-content:center; gap:6px; border:0; border-radius:5px; padding:10px 14px; min-height:46px; background:var(--primary-color,#007b83); color:var(--text-primary-color,#fff); }
        .feedback { font-size:13px; min-height:21px; margin-top:10px; } .feedback.error { color:var(--error-color,#bf3737); }
        .stats { display:grid; grid-template-columns:1fr 1fr; gap:24px; margin-top:24px; padding:24px 0; border-top:1px solid var(--divider-color,#d4dcda); }
        .stat-value { font-size:24px; font-weight:650; margin:5px 0; overflow-wrap:anywhere; }
        .stat-value.missing { font-size:17px; min-height:37px; display:flex; align-items:center; }
        .month { border-top:1px solid var(--divider-color,#d4dcda); margin-top:8px; padding-top:26px; }
        .month-grid { display:grid; grid-template-columns:1fr 1.2fr; gap:32px; margin:18px 0; }
        .month h3 { font-size:15px; font-weight:500; margin:0; }
        .month dl { margin:0; } .month dt { color:var(--secondary-text-color,#5a6563); } .month dd { margin:5px 0 12px; font-size:24px; font-weight:650; }
        table { border-collapse:collapse; width:100%; font-size:14px; } caption { text-align:left; font-weight:650; margin-bottom:10px; }
        th,td { text-align:left; padding:9px 0; border-bottom:1px solid var(--divider-color,#d4dcda); }
        th { font-size:12px; font-weight:500; color:var(--secondary-text-color,#5a6563); } th:last-child,td:last-child { text-align:right; padding-left:10px; white-space:nowrap; }
        td small { display:block; font-size:11px; } .peak-bar { height:4px; background:var(--primary-color,#007b83); margin-top:5px; border-radius:2px; max-width:100%; }
        .fine-print { font-size:13px; max-width:80ch; } .footer { margin-top:24px; padding-top:20px; border-top:1px solid var(--divider-color,#d4dcda); display:flex; flex-wrap:wrap; gap:16px; align-items:center; justify-content:space-between; }
        .settings { color:var(--primary-text-color,#202725); display:inline-flex; gap:8px; align-items:center; min-height:44px; text-underline-offset:3px; }
        .notice { margin-top:14px; font-size:13px; } .button-label { white-space:nowrap; }
        @media(max-width:680px) { main { padding:20px 16px; } .header { padding:8px 12px; } .hour,.month-grid { grid-template-columns:1fr; gap:22px; } .stats { gap:16px; } .reading { font-size:38px; } .threshold { padding:18px; } .intro { margin-bottom:14px; } }
        @media(prefers-reduced-motion:reduce) { .track-fill { transition:none; } }
      </style>
      <header class="header">
        <button class="icon-button" id="menu" aria-label="Åpne sidemeny" title="Åpne sidemeny"><ha-icon icon="mdi:menu"></ha-icon></button>
        <h1 id="name">Nettleievakt</h1><span class="beta">Beta</span>
      </header>
      <main>
        <div class="intro"><p>Følg forbruket før timen er over</p><small id="updated"></small></div>
        <section class="status" id="status" data-tone="neutral" aria-label="Målestatus">
          <ha-icon id="status-icon" icon="mdi:clock-outline"></ha-icon>
          <div role="status" aria-live="polite" aria-atomic="true"><h2 id="status-title">Venter på målinger</h2><p class="muted" id="status-description"></p></div>
        </section>
        <section aria-label="Denne timen" class="hour">
          <div>
            <p class="eyebrow">Anslått snitt for denne klokketimen</p>
            <p class="reading" id="forecast"></p>
            <p class="muted">Hvis effekten holder seg som ved siste måling.</p>
            <div id="gauge" data-tone="neutral" hidden>
              <div class="track" role="meter" id="meter" aria-label="Prognose mot varselgrense" aria-valuemin="0"><div class="track-fill" id="fill"></div></div>
              <div class="bar-labels"><span>0 kW</span><span id="gauge-target"></span></div>
              <p class="notice" id="margin"></p>
            </div>
          </div>
          <form class="threshold" id="target-form" novalidate>
            <label for="target">Din varselgrense</label>
            <p class="muted">Grensen gjelder snittet for en hel time, ikke et kort hopp i forbruket.</p>
            <div class="input-row">
              <div class="number-wrap"><input id="target" type="text" inputmode="decimal" maxlength="6" autocomplete="off" aria-describedby="target-help feedback" required><span aria-hidden="true">kW</span></div>
              <button class="save" id="save" type="submit" disabled><ha-icon icon="mdi:content-save-outline"></ha-icon><span class="button-label">Lagre</span></button>
            </div>
            <small id="target-help">Velg gjerne litt under nettleietrinnet ditt. For eksempel 4,5 kW hvis trinnet går ved 5 kW.</small>
            <p class="feedback" id="feedback" role="status" aria-live="polite"></p>
          </form>
        </section>
        <section class="stats" aria-label="Timens målinger">
          <div><h2 class="eyebrow">Kjøpt strøm hittil i timen</h2><p class="stat-value" id="energy"></p><small>Fra timens start til siste energimåling.</small></div>
          <div><h2 class="eyebrow">Plass til resten av timen</h2><p class="stat-value" id="budget"></p><small>Gjennomsnittlig effekt innenfor grensen. Ikke en grense for hva sikringene tåler.</small></div>
        </section>
        <section class="month" aria-labelledby="month-title">
          <h2 id="month-title">Denne måneden · det vi har målt</h2>
          <div class="month-grid">
            <div><h3 id="monthly-label"></h3><p class="stat-value" id="monthly"></p><p class="muted" id="monthly-help"></p>
              <dl style="margin-top:20px"><dt>Måledekning av måneden hittil</dt><dd id="coverage"></dd></dl>
            </div>
            <div><table id="peaks" hidden><caption>Høyeste målte time på hver toppdag</caption><thead><tr><th scope="col">Dato og time</th><th scope="col">Timesnitt</th></tr></thead><tbody id="peak-rows"></tbody></table><p class="muted" id="peaks-empty">Ingen hele timer å vise ennå.</p></div>
          </div>
          <p class="muted fine-print">Manglende målinger kan skjule høyere topper. Nettselskapets egne målinger og vilkår avgjør regningen. Nettleievakt henter ikke historikk fra før installasjonen.</p>
        </section>
        <footer class="footer"><p class="muted fine-print">Beta · ingen automatisk styring av utstyr.<br>Pushvarsler krever en egen varslingsautomatisering.</p><a class="settings" id="settings" href="/config/integrations/integration/nettleievakt"><ha-icon icon="mdi:cog-outline"></ha-icon>Innstillinger</a></footer>
      </main>`;
    this.$("menu").addEventListener("click", () => this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })));
    this.$("target").addEventListener("input", () => {
      this._dirty = true;
      this.$("target").removeAttribute("aria-invalid");
      this.feedback("");
      this.render();
    });
    this.$("target-form").addEventListener("submit", (event) => this.saveTarget(event));
    this.$("settings").addEventListener("click", (event) => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      history.pushState(null, "", this.$("settings").getAttribute("href"));
      window.dispatchEvent(new Event("location-changed"));
    });
  }

  $(id) { return this.shadowRoot.getElementById(id); }
  set hass(value) { this._hass = value; this.render(); }
  set panel(value) { this._panel = value; this.render(); }
  set narrow(value) { this.$("menu").hidden = !value; }
  connectedCallback() { this.render(); }
  text(id, value) { if (this.$(id).textContent !== value) this.$(id).textContent = value; }
  reading(id, value, unit) { this.text(id, format(value, unit)); this.$(id).classList.toggle("missing", value === null); }
  feedback(message, error = false) { this.text("feedback", message); this.$("feedback").classList.toggle("error", error); }

  render() {
    const config = this._panel?.config ?? {};
    const data = readDashboard(this._hass, config);
    this.text("name", config.name || "Nettleievakt");
    this.text("updated", data.connected ? measuredAt(data.lastMeasurement) : "Ingen forbindelse til Home Assistant");
    this.text("status-title", data.title);
    this.text("status-description", data.description);
    this.$("status").dataset.tone = data.tone;
    this.$("status-icon").setAttribute("icon", data.icon);
    this.reading("forecast", data.forecast, "kW");
    this.reading("energy", data.energy, "kWh");
    this.reading("budget", data.budget, "kW i snitt");
    this.reading("monthly", data.monthly, "kW");
    this.text("coverage", format(data.coverage, "%"));
    this.text("monthly-label", `Snitt av de ${data.peakDays} høyeste døgnmaksene`);
    this.text("monthly-help", !data.connected ? "Månedsverdiene vises når forbindelsen er tilbake." : data.monthly === null
      ? `Trenger hele timer på ${data.peakDays} ulike dager. Dette tallet er ikke klart ennå.`
      : "Foreløpig snitt, ikke en bekreftet nettleiekostnad. Dagens maksimum kan fortsatt øke.");
    const input = this.$("target");
    if (this._requestedTarget === data.target) this._requestedTarget = null;
    if (!this._dirty && !this._saving && this._requestedTarget == null && this.shadowRoot.activeElement !== input) {
      input.value = data.target === null ? "" : String(data.target).replace(".", ",");
    }
    input.disabled = this._saving || !data.connected || data.target === null;
    this.$("save").disabled = !this._dirty || input.disabled;
    this.$("target-form").setAttribute("aria-busy", String(this._saving));
    const showGauge = data.forecast !== null && data.target !== null && data.target > 0;
    this.$("gauge").hidden = !showGauge;
    if (showGauge) {
      this.$("gauge").dataset.tone = data.tone;
      this.$("fill").style.width = `${Math.min(100, Math.max(0, data.forecast / data.target * 100))}%`;
      this.$("meter").setAttribute("aria-valuemax", String(Math.max(data.target, data.forecast)));
      this.$("meter").setAttribute("aria-valuenow", String(Math.max(0, data.forecast)));
      this.$("meter").setAttribute("aria-valuetext", `${format(data.forecast, "kW")}, varselgrense ${format(data.target, "kW")}`);
      this.text("gauge-target", `Grense ${format(data.target, "kW")}`);
      const difference = data.target - data.forecast;
      this.text("margin", difference > 0 ? `${format(difference, "kW")} under grensen i prognosen.`
        : difference < 0 ? `${format(-difference, "kW")} over grensen i prognosen.` : "Prognosen er på varselgrensen.");
    }
    const signature = JSON.stringify(data.topDays);
    if (this._peaksSignature !== signature) {
      this._peaksSignature = signature;
      const rows = this.$("peak-rows");
      rows.replaceChildren();
      const maximum = Math.max(1, ...data.topDays.map((day) => day.kw));
      for (const day of data.topDays) {
        const label = peakLabel(day);
        const row = document.createElement("tr");
        const when = document.createElement("td");
        when.textContent = label.date;
        const hour = document.createElement("small");
        hour.textContent = label.hour;
        when.append(hour);
        const value = document.createElement("td");
        value.textContent = format(day.kw, "kW");
        const bar = document.createElement("div");
        bar.className = "peak-bar";
        bar.setAttribute("aria-hidden", "true");
        bar.style.width = `${day.kw / maximum * 100}%`;
        value.append(bar);
        row.append(when, value);
        rows.append(row);
      }
      this.$("peaks").hidden = data.topDays.length === 0;
      this.$("peaks-empty").hidden = data.topDays.length > 0;
    }
  }

  async saveTarget(event) {
    event.preventDefault();
    if (this._saving || !this._dirty) return;
    const value = parseTarget(this.$("target").value);
    if (value === null) {
      this.$("target").setAttribute("aria-invalid", "true");
      this.feedback("Velg 0,1–100 kW med maks én desimal.", true);
      this.$("target").focus();
      return;
    }
    const entityId = this._panel?.config?.entities?.target_kw;
    if (!entityId || this._hass?.connected === false) {
      this.feedback("Ingen forbindelse. Grensen er ikke endret.", true);
      return;
    }
    this._saving = true;
    this.feedback("Lagrer varselgrensen …");
    this.render();
    try {
      await this._hass.callService("number", "set_value", { value }, { entity_id: entityId });
      this._requestedTarget = value;
      this._dirty = false;
      this.feedback(`Grensen ${format(value, "kW")} er lagret. Målingene lastes inn på nytt.`);
    } catch {
      this.feedback("Kunne ikke lagre. Sjekk forbindelsen og at du har tilgang til å endre grensen. Prøv igjen.", true);
    } finally {
      this._saving = false;
      this.render();
    }
  }
}

if (!customElements.get("nettleievakt-panel")) customElements.define("nettleievakt-panel", NettleievaktPanel);
