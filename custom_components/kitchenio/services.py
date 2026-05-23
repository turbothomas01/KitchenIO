from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import DEFAULT_SHOPPING_LIST_ENTITY, DOMAIN

SERVICE_ADD_ITEM_TO_SHOPPING_LIST = "add_item_to_shopping_list"
DEFAULT_TODO_SHOPPING_LIST = "todo.shopping_list"


def _first_coordinator(hass: HomeAssistant) -> Any:
    coordinators = hass.data.get(DOMAIN, {})
    if not coordinators:
        raise HomeAssistantError("KitchenIO is not configured")
    return next(iter(coordinators.values()))


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register KitchenIO services."""
    if hass.services.has_service(DOMAIN, SERVICE_ADD_ITEM_TO_SHOPPING_LIST):
        return

    async def add_item_to_shopping_list(call: ServiceCall) -> None:
        coordinator = _first_coordinator(hass)
        stock_item_id = call.data.get("stock_item_id")
        name = call.data.get("name")
        amount = call.data.get("amount")

        if stock_item_id is not None:
            match = next(
                (item for item in coordinator.data if int(item.get("id", -1)) == stock_item_id),
                None,
            )
            if match is None:
                raise ServiceValidationError(f"KitchenIO stock item {stock_item_id} was not found")
            name = match.get("name")
            amount = match.get("amount")

        if not name:
            raise ServiceValidationError("Provide either stock_item_id or name")

        item_text = _shopping_item_text(str(name), amount)
        await hass.services.async_call(
            "todo",
            "add_item",
            {
                "entity_id": call.data.get("shopping_list_entity", DEFAULT_SHOPPING_LIST_ENTITY),
                "item": item_text,
            },
            blocking=True,
        )

    schema = vol.Schema(
        {
            vol.Optional("stock_item_id"): vol.Coerce(int),
            vol.Optional("name"): str,
            vol.Optional("amount"): str,
            vol.Optional("shopping_list_entity", default=DEFAULT_SHOPPING_LIST_ENTITY): str,
        }
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_ITEM_TO_SHOPPING_LIST,
        add_item_to_shopping_list,
        schema=schema,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister KitchenIO services."""
    hass.services.async_remove(DOMAIN, SERVICE_ADD_ITEM_TO_SHOPPING_LIST)


def _shopping_item_text(name: str, amount: Any) -> str:
    clean_name = name.strip()
    clean_amount = str(amount or "").strip()
    if not clean_amount:
        return clean_name
    return f"{clean_name} ({clean_amount})"
