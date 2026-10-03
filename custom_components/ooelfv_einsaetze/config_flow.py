"""Config- und Options-Flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    BEZIRKE,
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
    FILTER_ALL,
    FILTER_EXCLUDE,
    FILTER_ONLY,
    INTERVAL_OPTIONS,
    TARGET_ENTITY,
    TARGET_SERVICE,
)


def _notify_options(hass: HomeAssistant, selected: list[str]) -> list[SelectOptionDict]:
    """Alle notify-Dienste und -Entitäten als Auswahl (plus bereits gewählte)."""
    options: dict[str, str] = {}
    for service in hass.services.async_services_for_domain("notify"):
        if service != "send_message":
            options[f"{TARGET_SERVICE}{service}"] = f"Dienst: notify.{service}"
    for entity_id in hass.states.async_entity_ids("notify"):
        options[f"{TARGET_ENTITY}{entity_id}"] = f"Entität: {entity_id}"
    for value in selected:
        options.setdefault(value, f"{value} (derzeit nicht verfügbar)")
    return [
        SelectOptionDict(value=v, label=l)
        for v, l in sorted(options.items(), key=lambda kv: kv[1].casefold())
    ]


def _schema(hass: HomeAssistant, defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_BEZIRKE, default=defaults.get(CONF_BEZIRKE, [])
            ): SelectSelector(
                SelectSelectorConfig(
                    options=BEZIRKE,
                    multiple=True,
                    custom_value=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_SUBTYP_FILTER,
                default=defaults.get(CONF_SUBTYP_FILTER, DEFAULT_SUBTYP_FILTER),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[FILTER_ALL, FILTER_ONLY, FILTER_EXCLUDE],
                    translation_key="subtyp_filter",
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Required(
                CONF_INTERVAL,
                default=str(defaults.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=str(m), label=f"{m} Minuten")
                        for m in INTERVAL_OPTIONS
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_NOTIFY_TARGETS, default=defaults.get(CONF_NOTIFY_TARGETS, [])
            ): SelectSelector(
                SelectSelectorConfig(
                    options=_notify_options(
                        hass, defaults.get(CONF_NOTIFY_TARGETS, [])
                    ),
                    multiple=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_NOTIFY_NEW, default=defaults.get(CONF_NOTIFY_NEW, DEFAULT_NOTIFY_NEW)
            ): BooleanSelector(),
            vol.Required(
                CONF_NOTIFY_ENDED,
                default=defaults.get(CONF_NOTIFY_ENDED, DEFAULT_NOTIFY_ENDED),
            ): BooleanSelector(),
            vol.Required(
                CONF_NOTIFY_CHANGED,
                default=defaults.get(CONF_NOTIFY_CHANGED, DEFAULT_NOTIFY_CHANGED),
            ): BooleanSelector(),
            vol.Required(
                CONF_MIN_ALARMSTUFE,
                default=defaults.get(CONF_MIN_ALARMSTUFE, DEFAULT_MIN_ALARMSTUFE),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0, max=10, step=1, mode=NumberSelectorMode.BOX
                )
            ),
        }
    )


def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_BEZIRKE: user_input.get(CONF_BEZIRKE, []),
        CONF_SUBTYP_FILTER: user_input[CONF_SUBTYP_FILTER],
        CONF_INTERVAL: int(user_input[CONF_INTERVAL]),
        CONF_NOTIFY_TARGETS: user_input.get(CONF_NOTIFY_TARGETS, []),
        CONF_NOTIFY_NEW: user_input[CONF_NOTIFY_NEW],
        CONF_NOTIFY_ENDED: user_input[CONF_NOTIFY_ENDED],
        CONF_NOTIFY_CHANGED: user_input[CONF_NOTIFY_CHANGED],
        CONF_MIN_ALARMSTUFE: int(user_input[CONF_MIN_ALARMSTUFE]),
    }


class EinsaetzeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtung über die UI."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="OÖ Feuerwehr Einsätze", data={}, options=_clean(user_input)
            )
        return self.async_show_form(step_id="user", data_schema=_schema(self.hass, {}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return EinsaetzeOptionsFlow()


class EinsaetzeOptionsFlow(OptionsFlow):
    """Nachträgliche Änderung der Filter und des Abfrageintervalls."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=_clean(user_input))
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(self.hass, dict(self.config_entry.options)),
        )
