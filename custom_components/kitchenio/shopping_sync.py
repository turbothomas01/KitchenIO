from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval

from .const import DEFAULT_SCAN_INTERVAL, DEFAULT_SHOPPING_LIST_ENTITY, DOMAIN
from .coordinator import KitchenIOCoordinator

_LOGGER = logging.getLogger(__name__)
_AMOUNT_RE = re.compile(r"^(.+?)\s*\(([^()]+)\)\s*$")


@dataclass(frozen=True, slots=True)
class ShoppingEntry:
    """Normalized shopping-list item shared between Home Assistant and KitchenIO."""

    key: str
    name: str
    amount: str
    text: str
    source_id: Any = None


class KitchenIOShoppingSync:
    """Keep Home Assistant's default shopping list and KitchenIO in sync."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: KitchenIOCoordinator,
        shopping_list_entity: str = DEFAULT_SHOPPING_LIST_ENTITY,
    ) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.shopping_list_entity = shopping_list_entity
        self._known_ha_keys: set[str] = set()
        self._known_kitchenio_keys: set[str] = set()
        self._primed = False
        self._unsub: Callable[[], None] | None = None
        self._syncing = False

    async def async_start(self) -> None:
        """Start periodic sync and run once immediately."""
        await self.async_sync()
        self._unsub = async_track_time_interval(
            self.hass,
            lambda now: self.hass.async_create_task(self.async_sync()),
            DEFAULT_SCAN_INTERVAL,
        )

    async def async_stop(self) -> None:
        """Stop periodic sync."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    async def async_sync(self) -> None:
        """Synchronize open shopping-list items both ways."""
        if self._syncing:
            return
        self._syncing = True
        try:
            ha_items = await self._async_get_ha_items()
            kitchenio_items = await self._async_get_kitchenio_items()
            ha_by_key = {item.key: item for item in ha_items}
            kitchenio_by_key = {item.key: item for item in kitchenio_items}

            if not self._primed:
                await self._copy_missing_items(ha_by_key, kitchenio_by_key)
                self._primed = True
            else:
                await self._apply_bidirectional_changes(ha_by_key, kitchenio_by_key)

            ha_items = await self._async_get_ha_items()
            kitchenio_items = await self._async_get_kitchenio_items()
            self._known_ha_keys = {item.key for item in ha_items}
            self._known_kitchenio_keys = {item.key for item in kitchenio_items}
            await self.coordinator.async_request_refresh()
        except Exception:  # noqa: BLE001 - keep HA running if sync fails.
            _LOGGER.exception("KitchenIO shopping-list sync failed")
        finally:
            self._syncing = False

    async def _copy_missing_items(
        self,
        ha_by_key: dict[str, ShoppingEntry],
        kitchenio_by_key: dict[str, ShoppingEntry],
    ) -> None:
        """Initial sync: preserve both lists by taking the union."""
        for key, item in ha_by_key.items():
            if key not in kitchenio_by_key:
                await self.coordinator.client.async_add_shopping_item(item.name, item.amount)
        for key, item in kitchenio_by_key.items():
            if key not in ha_by_key:
                await self._async_add_ha_item(item.text)

    async def _apply_bidirectional_changes(
        self,
        ha_by_key: dict[str, ShoppingEntry],
        kitchenio_by_key: dict[str, ShoppingEntry],
    ) -> None:
        """Sync additions and removals after the initial union pass."""
        ha_keys = set(ha_by_key)
        kitchenio_keys = set(kitchenio_by_key)

        removed_from_ha = self._known_ha_keys - ha_keys
        removed_from_kitchenio = self._known_kitchenio_keys - kitchenio_keys

        for key in sorted(removed_from_ha & kitchenio_keys):
            await self.coordinator.client.async_delete_shopping_item(kitchenio_by_key[key].source_id)
            kitchenio_by_key.pop(key, None)
            kitchenio_keys.discard(key)

        for key in sorted(removed_from_kitchenio & ha_keys):
            await self._async_remove_ha_item(ha_by_key[key].text)
            ha_by_key.pop(key, None)
            ha_keys.discard(key)

        for key, item in ha_by_key.items():
            if key not in kitchenio_keys:
                await self.coordinator.client.async_add_shopping_item(item.name, item.amount)

        for key, item in kitchenio_by_key.items():
            if key not in ha_keys:
                await self._async_add_ha_item(item.text)

    async def _async_get_kitchenio_items(self) -> list[ShoppingEntry]:
        items = await self.coordinator.client.async_shopping_list()
        return [
            _entry_from_parts(item["item"], item.get("amount") or "1", source_id=item.get("id"))
            for item in items
            if not item.get("completed")
        ]

    async def _async_get_ha_items(self) -> list[ShoppingEntry]:
        response = await self.hass.services.async_call(
            "todo",
            "get_items",
            {"entity_id": self.shopping_list_entity, "status": ["needs_action"]},
            blocking=True,
            return_response=True,
        )
        raw_items = _extract_todo_items(response, self.shopping_list_entity)
        entries: list[ShoppingEntry] = []
        for raw in raw_items:
            text = str(raw.get("summary") or raw.get("item") or "").strip()
            if text:
                entries.append(_entry_from_text(text))
        return entries

    async def _async_add_ha_item(self, text: str) -> None:
        await self.hass.services.async_call(
            "todo",
            "add_item",
            {"entity_id": self.shopping_list_entity, "item": text},
            blocking=True,
        )

    async def _async_remove_ha_item(self, text: str) -> None:
        await self.hass.services.async_call(
            "todo",
            "remove_item",
            {"entity_id": self.shopping_list_entity, "item": text},
            blocking=True,
        )


def _extract_todo_items(response: Any, entity_id: str) -> list[dict[str, Any]]:
    if not isinstance(response, dict):
        raise HomeAssistantError("Unexpected response from todo.get_items")
    entity_response = response.get(entity_id) or response.get("response") or response
    if isinstance(entity_response, dict) and isinstance(entity_response.get("items"), list):
        return entity_response["items"]
    if isinstance(entity_response, list):
        return entity_response
    raise HomeAssistantError("Could not read items from todo.get_items response")


def _entry_from_text(text: str) -> ShoppingEntry:
    clean = " ".join(text.strip().split())
    match = _AMOUNT_RE.match(clean)
    if match:
        return _entry_from_parts(match.group(1), match.group(2))
    return _entry_from_parts(clean, "1")


def _entry_from_parts(name: str, amount: str, source_id: Any = None) -> ShoppingEntry:
    clean_name = " ".join(str(name).strip().split())
    clean_amount = " ".join(str(amount or "1").strip().split()) or "1"
    text = f"{clean_name} ({clean_amount})"
    key = f"{clean_name.casefold()}\u241f{clean_amount.casefold()}"
    return ShoppingEntry(key=key, name=clean_name, amount=clean_amount, text=text, source_id=source_id)
