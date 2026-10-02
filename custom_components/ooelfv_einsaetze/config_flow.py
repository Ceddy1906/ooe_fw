"""Config- und Options-Flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    BEZIRKE,
    CONF_BEZIRKE,
    CONF_INTERVAL,
    CONF_SUBTYP_FILTER,
    DEFAULT_INTERVAL,
    DEFAULT_SUBTYP_FILTER,
    DOMAIN,
    FILTER_ALL,
    FILTER_EXCLUDE,
    FILTER_ONLY,
    INTERVAL_OPTIONS,
)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
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
        }
    )


def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_BEZIRKE: user_input.get(CONF_BEZIRKE, []),
        CONF_SUBTYP_FILTER: user_input[CONF_SUBTYP_FILTER],
        CONF_INTERVAL: int(user_input[CONF_INTERVAL]),
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
        return self.async_show_form(step_id="user", data_schema=_schema({}))

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
            step_id="init", data_schema=_schema(dict(self.config_entry.options))
        )
