"""Versand der Benachrichtigungen."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import TARGET_ENTITY, TARGET_SERVICE

_LOGGER = logging.getLogger(__name__)


async def async_send(
    hass: HomeAssistant,
    targets: list[str],
    title: str,
    message: str,
    url: str | None = None,
) -> None:
    """Sendet title/message an alle ausgewählten Ziele; Fehler werden nur geloggt."""
    calls = []
    for target in targets:
        if target.startswith(TARGET_SERVICE):
            service = target.removeprefix(TARGET_SERVICE)
            data: dict[str, Any] = {"title": title, "message": message}
            if url and service.startswith("mobile_app_"):
                data["data"] = {"url": url, "clickAction": url}
            calls.append(hass.services.async_call("notify", service, data, blocking=True))
        elif target.startswith(TARGET_ENTITY):
            calls.append(
                hass.services.async_call(
                    "notify",
                    "send_message",
                    {
                        "entity_id": target.removeprefix(TARGET_ENTITY),
                        "title": title,
                        "message": message,
                    },
                    blocking=True,
                )
            )

    results = await asyncio.gather(*calls, return_exceptions=True)
    for target, result in zip(targets, results):
        if isinstance(result, Exception):
            _LOGGER.warning("Benachrichtigung an %s fehlgeschlagen: %s", target, result)
