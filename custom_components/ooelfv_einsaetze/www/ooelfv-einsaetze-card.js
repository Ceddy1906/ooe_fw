/* OÖ Feuerwehr Einsätze – Lovelace Card */

const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );

class OoelfvEinsaetzeCard extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  connectedCallback() {
    if (this._bound) return;
    this._bound = true;
    let holdTimer = null;
    let held = false;
    let tapTimer = null;

    const isLink = (ev) => ev.composedPath().some((n) => n.tagName === "A");

    this.addEventListener("pointerdown", (ev) => {
      held = false;
      if (isLink(ev) || !this._hasAction("hold_action")) return;
      holdTimer = setTimeout(() => {
        held = true;
        this._fire("hold");
      }, 500);
    });
    const cancelHold = () => clearTimeout(holdTimer);
    this.addEventListener("pointerup", cancelHold);
    this.addEventListener("pointerleave", cancelHold);
    this.addEventListener("pointercancel", cancelHold);
    this.addEventListener("pointermove", (ev) => {
      if (Math.abs(ev.movementX) + Math.abs(ev.movementY) > 6) cancelHold();
    });
    this.addEventListener("contextmenu", (ev) => {
      if (this._hasAction("hold_action")) ev.preventDefault();
    });

    this.addEventListener("click", (ev) => {
      if (isLink(ev) || held) return;
      if (this._hasAction("double_tap_action")) {
        if (tapTimer) {
          clearTimeout(tapTimer);
          tapTimer = null;
          this._fire("double_tap");
        } else {
          tapTimer = setTimeout(() => {
            tapTimer = null;
            this._fire("tap");
          }, 250);
        }
      } else {
        this._fire("tap");
      }
    });
  }

  _hasAction(name) {
    const a = this._config && this._config[name];
    return !!a && a.action !== "none";
  }

  _fire(action) {
    const c = this._config;
    if (!c || !c.entity) return;
    const config = {
      entity: c.entity,
      tap_action: c.tap_action || { action: "more-info" },
      hold_action: c.hold_action,
      double_tap_action: c.double_tap_action,
    };
    this.dispatchEvent(
      new CustomEvent("hass-action", {
        bubbles: true,
        composed: true,
        detail: { config, action },
      })
    );
  }

  static getConfigElement() {
    return document.createElement("ooelfv-einsaetze-card-editor");
  }

  // Layout-Tab im Bereiche-Dashboard: Spalten/Zeilen einstellbar
  getGridOptions() {
    return { columns: 12, rows: "auto", min_columns: 6, min_rows: 2 };
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

    const tap = this._config.tap_action;
    this.style.cursor = tap && tap.action === "none" ? "" : "pointer";

    const st = this._config.entity && this._hass.states[this._config.entity];
    let body;
    if (!this._config.entity) {
      body = `<div class="empty">Bitte eine Entität auswählen.</div>`;
    } else if (!st) {
      body = `<div class="empty">Entität ${esc(this._config.entity)} nicht gefunden.</div>`;
    } else {
      const max = this._config.max_einsaetze || 10;
      const all = st.attributes && st.attributes.einsaetze;
      const list = (Array.isArray(all) ? all : []).slice(0, max);
      body = list.length
        ? list.map((e) => this._einsatz(e)).join("")
        : `<div class="empty">Keine Einsätze</div>`;
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

const EDITOR_LABELS = {
  entity: "Entität",
  title: "Titel",
  max_einsaetze: "Max. Anzahl Einsätze",
  interactions: "Interaktionen",
  tap_action: "Aktion beim Tippen",
  hold_action: "Aktion beim Halten",
  double_tap_action: "Aktion bei Doppeltipp",
};

const EDITOR_SCHEMA = [
  {
    name: "entity",
    required: true,
    selector: { entity: { domain: "sensor", integration: "ooelfv_einsaetze" } },
  },
  { name: "title", selector: { text: {} } },
  {
    name: "max_einsaetze",
    selector: { number: { min: 1, max: 20, step: 1, mode: "box" } },
  },
  {
    type: "expandable",
    name: "interactions",
    title: "Interaktionen",
    flatten: true,
    schema: [
      { name: "tap_action", selector: { ui_action: { default_action: "more-info" } } },
      { name: "hold_action", selector: { ui_action: { default_action: "none" } } },
      { name: "double_tap_action", selector: { ui_action: { default_action: "none" } } },
    ],
  },
];

class OoelfvEinsaetzeCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  _update() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) => EDITOR_LABELS[schema.name] || schema.name;
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: ev.detail.value },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = EDITOR_SCHEMA;
    this._form.data = this._config;
  }
}

customElements.define("ooelfv-einsaetze-card-editor", OoelfvEinsaetzeCardEditor);
