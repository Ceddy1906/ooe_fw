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
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_URL,
    CONF_BEZIRKE,
    CONF_INTERVAL,
    CONF_SUBTYP_FILTER,
    DEFAULT_INTERVAL,
    DEFAULT_SUBTYP_FILTER,
    DOMAIN,
    FILTER_EXCLUDE,
    FILTER_ONLY,
    SUBTYP_UEBUNG_TEXT,
)

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


class EinsaetzeCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Holt die laufenden Einsätze und wendet die Filter an."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        interval = entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval),
        )
        self._bezirke = {_norm(b) for b in entry.options.get(CONF_BEZIRKE, [])}
        self._subtyp_filter = entry.options.get(
            CONF_SUBTYP_FILTER, DEFAULT_SUBTYP_FILTER
        )

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
        return result

    def _matches(self, e: dict[str, Any]) -> bool:
        if self._bezirke and _norm(e["bezirk"] or "") not in self._bezirke:
            return False
        is_uebung = e["einsatzsubtyp"] == SUBTYP_UEBUNG_TEXT
        if self._subtyp_filter == FILTER_ONLY and not is_uebung:
            return False
        if self._subtyp_filter == FILTER_EXCLUDE and is_uebung:
            return False
        return True

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
