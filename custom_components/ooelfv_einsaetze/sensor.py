"""Sensor: laufende Einsätze."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EinsaetzeConfigEntry
from .const import DOMAIN
from .coordinator import EinsaetzeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EinsaetzeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([EinsaetzeSensor(entry.runtime_data, entry)])


class EinsaetzeSensor(CoordinatorEntity[EinsaetzeCoordinator], SensorEntity):
    """Anzahl der gefilterten Einsätze, Details als Attribut."""

    _attr_has_entity_name = True
    _attr_translation_key = "einsaetze"
    _attr_icon = "mdi:fire-truck"
    _attr_native_unit_of_measurement = "Einsätze"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _unrecorded_attributes = frozenset({"einsaetze"})

    def __init__(self, coordinator: EinsaetzeCoordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_einsaetze"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"einsaetze": self.coordinator.data}
