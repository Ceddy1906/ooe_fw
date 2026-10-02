/* OÖ Feuerwehr Einsätze – Lovelace Card */

const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );

class OoelfvEinsaetzeCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error("Bitte 'entity' angeben (sensor.…_aktuelle_einsaetze).");
    }
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 4;
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find(
      (id) =>
        id.startsWith("sensor.") &&
        Array.isArray(hass.states[id].attributes.einsaetze)
    );
    return { entity: entity || "sensor.oo_feuerwehr_einsaetze_aktuelle_einsaetze" };
  }

  _fmtStart(iso) {
    if (!iso) return "–";
    const d = new Date(iso);
    const min = Math.max(0, Math.round((Date.now() - d.getTime()) / 60000));
    const rel =
      min < 60 ? `vor ${min} Min.` : `vor ${Math.floor(min / 60)} Std. ${min % 60} Min.`;
    const abs = d.toLocaleString("de-AT", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
    return `${abs} Uhr (${rel})`;
  }

  _row(icon, label, value) {
    return `
      <div class="row">
        <ha-icon icon="${icon}"></ha-icon>
        <div><div class="label">${label}</div><div class="value">${value}</div></div>
      </div>`;
  }

  _einsatz(e) {
    const wo = [e.strasse, e.zusatz, e.bereich || e.gemeinde]
      .filter(Boolean)
      .map(esc)
      .join(", ");
    const karte = e.karte
      ? ` <a href="${esc(e.karte)}" target="_blank" rel="noopener noreferrer">Karte</a>`
      : "";
    const typ = [e.einsatztyp, e.einsatzsubtyp]
      .filter((v, i, a) => v && a.indexOf(v) === i)
      .map(esc)
      .join(" – ");
    const wehren = (e.feuerwehren || []).length
      ? `<ul>${e.feuerwehren.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>`
      : "–";
    const stufe = Number(e.alarmstufe) || 0;

    return `
      <div class="einsatz stufe${Math.min(stufe, 3)}">
        <div class="head">
          <span class="typ">${esc(e.einsatztyp || "Einsatz")}</span>
          <span class="badge">Alarmstufe ${esc(e.alarmstufe ?? "–")}</span>
        </div>
        ${this._row("mdi:clock-start", "Beginn", esc(this._fmtStart(e.beginn)))}
        ${this._row("mdi:fire-truck", "Feuerwehren vor Ort", wehren)}
        ${this._row("mdi:alert-octagon", "Alarmstufe", esc(e.alarmstufe ?? "–"))}
        ${this._row("mdi:map-marker-radius", "Einsatzort", esc(e.einsatzort || "–"))}
        ${this._row("mdi:format-list-bulleted-type", "Einsatztyp", typ || "–")}
        ${this._row("mdi:map-marker", "Wo", (wo || "–") + karte)}
      </div>`;
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });

    const st = this._hass.states[this._config.entity];
    let body;
    if (!st) {
      body = `<div class="empty">Entität ${esc(this._config.entity)} nicht gefunden.</div>`;
    } else {
      const max = this._config.max_einsaetze || 10;
      const list = (st.attributes.einsaetze || []).slice(0, max);
      body = list.length
        ? list.map((e) => this._einsatz(e)).join("")
        : `<div class="empty">Keine aktuellen Einsätze</div>`;
    }

    this.shadowRoot.innerHTML = `
      <style>
        .einsatz { border-left: 4px solid var(--primary-color); margin: 0 16px 16px; padding: 4px 0 4px 12px; }
        .einsatz.stufe1 { border-color: var(--warning-color, orange); }
        .einsatz.stufe2, .einsatz.stufe3 { border-color: var(--error-color, red); }
        .head { display: flex; justify-content: space-between; align-items: center; font-weight: 500; font-size: 1.1em; margin-bottom: 6px; }
        .badge { font-size: .75em; padding: 2px 8px; border-radius: 10px; background: var(--secondary-background-color); }
        .row { display: flex; gap: 12px; align-items: flex-start; margin: 6px 0; }
        .row ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); margin-top: 2px; }
        .label { font-size: .75em; color: var(--secondary-text-color); }
        .value ul { margin: 0; padding-left: 18px; }
        a { color: var(--primary-color); }
        .empty { padding: 16px; color: var(--secondary-text-color); }
      </style>
      <ha-card header="${esc(this._config.title || "Feuerwehr Einsätze")}">${body}</ha-card>`;
  }
}

customElements.define("ooelfv-einsaetze-card", OoelfvEinsaetzeCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "ooelfv-einsaetze-card",
  name: "OÖ Feuerwehr Einsätze",
  description: "Zeigt laufende Feuerwehreinsätze aus Oberösterreich.",
});
