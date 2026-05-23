from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KitchenIOCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KitchenIO stock sensor."""
    coordinator: KitchenIOCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KitchenIOStockSensor(coordinator, entry)])


class KitchenIOStockSensor(CoordinatorEntity[KitchenIOCoordinator], SensorEntity):
    """Summary sensor for stock held in KitchenIO."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:fridge-outline"
    _attr_translation_key = "stock"

    def __init__(self, coordinator: KitchenIOCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_stock"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="KitchenIO",
            model="KitchenIO local API",
        )

    @property
    def native_value(self) -> int:
        """Return the number of stock items currently in stock."""
        return len([item for item in self.coordinator.data if _is_in_stock(item)])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the stock list in attributes for dashboard cards and automations."""
        items = [_normalise_item(item) for item in self.coordinator.data if _is_in_stock(item)]
        low_stock_items = [item for item in items if _is_low_stock(item)]
        return {
            "items": items,
            "low_stock_items": low_stock_items,
            "stock_table": _stock_table(items),
        }


def _normalise_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": str(item.get("name", "")).strip(),
        "amount": str(item.get("amount", "")).strip(),
        "description": str(item.get("description", "")).strip(),
    }


def _is_in_stock(item: dict[str, Any]) -> bool:
    amount = str(item.get("amount", "")).strip()
    if not amount:
        return False
    try:
        return Decimal(amount.split(maxsplit=1)[0].replace(",", ".")) > 0
    except (InvalidOperation, ValueError):
        return True


def _is_low_stock(item: dict[str, Any]) -> bool:
    amount = str(item.get("amount", "")).strip()
    try:
        return Decimal(amount.split(maxsplit=1)[0].replace(",", ".")) <= 1
    except (InvalidOperation, ValueError):
        return False


def _stock_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No KitchenIO stock items are currently in stock."
    lines = ["| Item | Amount |", "| --- | ---: |"]
    for item in sorted(items, key=lambda row: row["name"].casefold()):
        name = item["name"].replace("|", "\|")
        amount = item["amount"].replace("|", "\|")
        lines.append(f"| {name} | {amount} |")
    return "\n".join(lines)
