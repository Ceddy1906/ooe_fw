"""OÖ Feuerwehr Einsätze."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, DOMAIN
from .coordinator import EinsaetzeCoordinator

PLATFORMS = ["sensor", "binary_sensor"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type EinsaetzeConfigEntry = ConfigEntry[EinsaetzeCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Lovelace-Card automatisch bereitstellen."""
    card = Path(__file__).parent / "www" / "ooelfv-einsaetze-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card), False)]
    )
    add_extra_js_url(hass, CARD_URL)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: EinsaetzeConfigEntry) -> bool:
    coordinator = EinsaetzeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EinsaetzeConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: EinsaetzeConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
