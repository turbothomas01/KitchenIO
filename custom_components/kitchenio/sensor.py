from __future__ import annotations

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
    """Set up KitchenIO product sensor."""
    coordinator: KitchenIOCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([KitchenIOProductSensor(coordinator, entry)])


class KitchenIOProductSensor(CoordinatorEntity[KitchenIOCoordinator], SensorEntity):
    """Summary sensor for products in KitchenIO."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:cart-outline"
    _attr_translation_key = "products"

    def __init__(self, coordinator: KitchenIOCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_products"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="KitchenIO",
            model="KitchenIO local API",
        )

    @property
    def native_value(self) -> int:
        """Return the number of active KitchenIO products."""
        return len([item for item in self.coordinator.data if not item.get("completed")])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the product list in attributes for dashboard cards and automations."""
        items = [_normalise_item(item) for item in self.coordinator.data if not item.get("completed")]
        return {
            "items": items,
            "product_table": _product_table(items),
        }


def _normalise_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": str(item.get("item", item.get("name", ""))).strip(),
        "amount": str(item.get("amount", "")).strip(),
    }


def _product_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No KitchenIO products yet."
    lines = ["| Product | Amount |", "| --- | ---: |"]
    for item in sorted(items, key=lambda row: row["name"].casefold()):
        name = item["name"].replace("|", "\\|")
        amount = item["amount"].replace("|", "\\|")
        lines.append(f"| {name} | {amount} |")
    return "\n".join(lines)
