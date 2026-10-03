"""DataUpdateCoordinator für OÖ Feuerwehr Einsätze."""

from __future__ import annotations

from datetime import timedelta
from email.utils import parsedate_to_datetime
import json
import logging
import re
from typing import Any

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_URL,
    CONF_BEZIRKE,
    CONF_INTERVAL,
    CONF_MIN_ALARMSTUFE,
    CONF_NOTIFY_CHANGED,
    CONF_NOTIFY_ENDED,
    CONF_NOTIFY_NEW,
    CONF_NOTIFY_TARGETS,
    CONF_SUBTYP_FILTER,
    DEFAULT_INTERVAL,
    DEFAULT_MIN_ALARMSTUFE,
    DEFAULT_NOTIFY_CHANGED,
    DEFAULT_NOTIFY_ENDED,
    DEFAULT_NOTIFY_NEW,
    DEFAULT_SUBTYP_FILTER,
    DOMAIN,
    EVENT_CHANGED,
    EVENT_ENDED,
    EVENT_NEW,
    FILTER_EXCLUDE,
    FILTER_ONLY,
    STORE_MAX_AGE_HOURS,
    STORE_VERSION,
    SUBTYP_UEBUNG_TEXT,
)
from .notifier import async_send

_LOGGER = logging.getLogger(__name__)


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _clean_fw_name(name: str) -> str:
    name = re.sub(r"^Feuerwehr/Florian\s+", "", name)
    return re.sub(r"\s*\(\d+\)$", "", name).strip()


def _parse_time(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError):
        return None


def _stufe(e: dict[str, Any]) -> int:
    try:
        return int(e.get("alarmstufe") or 0)
    except (TypeError, ValueError):
        return 0


def _fmt_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} Min."
    return f"{minutes // 60} Std. {minutes % 60} Min."


class EinsaetzeCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Holt die laufenden Einsätze, filtert sie und meldet Änderungen."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        opts = entry.options
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=opts.get(CONF_INTERVAL, DEFAULT_INTERVAL)
            ),
        )
        self._bezirke = {_norm(b) for b in opts.get(CONF_BEZIRKE, [])}
        self._subtyp_filter = opts.get(CONF_SUBTYP_FILTER, DEFAULT_SUBTYP_FILTER)

        self._targets: list[str] = opts.get(CONF_NOTIFY_TARGETS, [])
        self._notify_new = opts.get(CONF_NOTIFY_NEW, DEFAULT_NOTIFY_NEW)
        self._notify_ended = opts.get(CONF_NOTIFY_ENDED, DEFAULT_NOTIFY_ENDED)
        self._notify_changed = opts.get(CONF_NOTIFY_CHANGED, DEFAULT_NOTIFY_CHANGED)
        self._min_stufe = int(opts.get(CONF_MIN_ALARMSTUFE, DEFAULT_MIN_ALARMSTUFE))

        # Gemerkte Einsätze (Nummer -> Daten). None = noch kein Vergleichsstand,
        # der erste Abruf legt dann nur die Basis an und meldet nichts.
        self._known: dict[str, dict[str, Any]] | None = None
        self._signature = json.dumps(
            [sorted(self._bezirke), self._subtyp_filter], ensure_ascii=False
        )
        self._store: Store = Store(hass, STORE_VERSION, f"{DOMAIN}.known")

    async def _async_setup(self) -> None:
        """Gemerkte Einsätze laden, sofern sie zu den aktuellen Filtern passen."""
        data = await self._store.async_load()
        if not data or data.get("signature") != self._signature:
            return
        saved = dt_util.parse_datetime(data.get("saved", ""))
        if saved is None or dt_util.utcnow() - saved > timedelta(
            hours=STORE_MAX_AGE_HOURS
        ):
            return
        self._known = data.get("known", {})

    async def _async_update_data(self) -> list[dict[str, Any]]:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(API_URL, timeout=30) as resp:
                resp.raise_for_status()
                payload = json.loads(await resp.text())
        except (ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Abruf der Einsatzdaten fehlgeschlagen: {err}") from err

        raw = payload.get("einsaetze") if isinstance(payload, dict) else None
        raw = raw or {}
        items = raw.values() if isinstance(raw, dict) else raw

        result: list[dict[str, Any]] = []
        for item in items:
            einsatz = item.get("einsatz", item) if isinstance(item, dict) else None
            if not einsatz:
                continue
            parsed = self._parse(einsatz)
            if self._matches(parsed):
                result.append(parsed)

        result.sort(key=lambda e: e["beginn"] or "", reverse=True)
        await self._process_changes(result)
        return result

    # ------------------------------------------------------------------ Filter

    def _matches(self, e: dict[str, Any]) -> bool:
        if self._bezirke and _norm(e["bezirk"] or "") not in self._bezirke:
            return False
        is_uebung = e["einsatzsubtyp"] == SUBTYP_UEBUNG_TEXT
        if self._subtyp_filter == FILTER_ONLY and not is_uebung:
            return False
        if self._subtyp_filter == FILTER_EXCLUDE and is_uebung:
            return False
        return True

    # ----------------------------------------------------------- Änderungen

    async def _process_changes(self, current_list: list[dict[str, Any]]) -> None:
        current = {e["nummer"]: e for e in current_list if e["nummer"]}

        if self._known is None:
            # Basis anlegen, bereits laufende Einsätze nicht melden
            self._known = current
            self._save()
            return

        for nummer, e in current.items():
            old = self._known.get(nummer)
            if old is None:
                await self._on_new(e)
                continue
            neue_wehren = [w for w in e["feuerwehren"] if w not in old["feuerwehren"]]
            if _stufe(e) > _stufe(old) or neue_wehren:
                await self._on_changed(old, e, neue_wehren)

        for nummer, old in self._known.items():
            if nummer not in current:
                await self._on_ended(old)

        self._known = current
        self._save()

    def _save(self) -> None:
        self._store.async_delay_save(
            lambda: {
                "signature": self._signature,
                "saved": dt_util.utcnow().isoformat(),
                "known": self._known,
            },
            10,
        )

    @staticmethod
    def _describe(e: dict[str, Any]) -> list[str]:
        zeilen = [e["einsatzort"] or e["gemeinde"] or "–"]
        wo = ", ".join(p for p in (e["strasse"], e["zusatz"], e["bereich"]) if p)
        if wo:
            zeilen.append(wo)
        typ = " – ".join(
            dict.fromkeys(p for p in (e["einsatztyp"], e["einsatzsubtyp"]) if p)
        )
        if typ:
            zeilen.append(typ)
        zeilen.append(f"Alarmstufe {e['alarmstufe'] if e['alarmstufe'] is not None else '–'}")
        if e["beginn"]:
            start = dt_util.as_local(dt_util.parse_datetime(e["beginn"]))
            zeilen.append(f"Beginn: {start:%H:%M} Uhr")
        if e["feuerwehren"]:
            zeilen.append("Feuerwehren: " + ", ".join(e["feuerwehren"]))
        return zeilen

    async def _notify(self, enabled: bool, e: dict[str, Any], title: str, text: list[str]) -> None:
        if not (enabled and self._targets and _stufe(e) >= self._min_stufe):
            return
        await async_send(self.hass, self._targets, title, "\n".join(text), e["karte"])

    async def _on_new(self, e: dict[str, Any]) -> None:
        self.hass.bus.async_fire(EVENT_NEW, e)
        await self._notify(
            self._notify_new,
            e,
            f"🚒 Neuer Einsatz: {e['einsatztyp'] or 'Einsatz'}",
            self._describe(e),
        )

    async def _on_changed(
        self, old: dict[str, Any], e: dict[str, Any], neue_wehren: list[str]
    ) -> None:
        aenderungen = []
        if _stufe(e) > _stufe(old):
            aenderungen.append(f"Alarmstufe {old['alarmstufe']} → {e['alarmstufe']}")
        if neue_wehren:
            aenderungen.append("Weitere Feuerwehren: " + ", ".join(neue_wehren))
        self.hass.bus.async_fire(
            EVENT_CHANGED, {**e, "aenderungen": aenderungen, "neue_feuerwehren": neue_wehren}
        )
        await self._notify(
            self._notify_changed,
            e,
            f"⚠️ Einsatz aktualisiert: {e['einsatztyp'] or 'Einsatz'}",
            aenderungen + self._describe(e),
        )

    async def _on_ended(self, e: dict[str, Any]) -> None:
        dauer = None
        if e["beginn"]:
            start = dt_util.parse_datetime(e["beginn"])
            dauer = max(0, int((dt_util.utcnow() - start).total_seconds() // 60))
        self.hass.bus.async_fire(EVENT_ENDED, {**e, "dauer_minuten": dauer})
        zeilen = self._describe(e)
        if dauer is not None:
            zeilen.append(f"Dauer: ca. {_fmt_duration(dauer)}")
        await self._notify(
            self._notify_ended,
            e,
            f"✅ Einsatz beendet: {e['einsatztyp'] or 'Einsatz'}",
            zeilen,
        )

    # ------------------------------------------------------------------ Parser

    @staticmethod
    def _parse(e: dict[str, Any]) -> dict[str, Any]:
        adresse = e.get("adresse") or {}
        wgs = e.get("wgs84") or {}

        wehren = [
            _clean_fw_name(fw.get("fwname", ""))
            for fw in (e.get("feuerwehrenarray") or {}).values()
        ]
        if not wehren:
            wehren = [
                _clean_fw_name(fw.get("feuerwehr", ""))
                for fw in (e.get("feuerwehren") or {}).values()
            ]
        wehren = [w for w in wehren if w]

        strasse = " ".join(
            p for p in (adresse.get("efeanme"), adresse.get("estnum")) if p
        )
        lat, lng = wgs.get("lat"), wgs.get("lng")
        karte = None
        if lat and lng:
            karte = (
                f"https://www.openstreetmap.org/?mlat={lat}&mlon={lng}"
                f"#map=16/{lat}/{lng}"
            )

        return {
            "nummer": e.get("num1"),
            "beginn": _parse_time(e.get("startzeit")),
            "status": e.get("status"),
            "alarmstufe": e.get("alarmstufe"),
            "einsatzort": e.get("einsatzort"),
            "einsatztyp": (e.get("einsatztyp") or {}).get("text"),
            "einsatzsubtyp": (e.get("einsatzsubtyp") or {}).get("text"),
            "bezirk": (e.get("bezirk") or {}).get("text"),
            "gemeinde": adresse.get("emun") or adresse.get("default"),
            "bereich": adresse.get("earea"),
            "strasse": strasse or None,
            "zusatz": adresse.get("ecompl") or None,
            "latitude": lat,
            "longitude": lng,
            "karte": karte,
            "feuerwehren": wehren,
        }
