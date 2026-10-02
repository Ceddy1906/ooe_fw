"""Binary-Sensor: ist aktuell ein (gefilterter) Einsatz aktiv?"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EinsaetzeConfigEntry
from .coordinator import EinsaetzeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EinsaetzeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([EinsatzAktivSensor(entry.runtime_data, entry)])


class EinsatzAktivSensor(CoordinatorEntity[EinsaetzeCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "einsatz_aktiv"
    _attr_icon = "mdi:fire-alert"

    def __init__(self, coordinator: EinsaetzeCoordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_einsatz_aktiv"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data)
