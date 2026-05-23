from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import KitchenIOApiError, KitchenIOClient
from .const import CONF_API_KEY, CONF_URL, DEFAULT_NAME, DOMAIN


class KitchenIOConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the KitchenIO config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_URL].rstrip("/"))
            self._abort_if_unique_id_configured()
            session = async_create_clientsession(self.hass)
            client = KitchenIOClient(
                session=session,
                url=user_input[CONF_URL],
                api_key=user_input.get(CONF_API_KEY) or None,
            )
            try:
                await client.async_health()
            except KitchenIOApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or DEFAULT_NAME,
                    data={
                        CONF_NAME: user_input.get(CONF_NAME) or DEFAULT_NAME,
                        CONF_URL: user_input[CONF_URL].rstrip("/"),
                        CONF_API_KEY: user_input.get(CONF_API_KEY, ""),
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_URL, default="http://192.168.0.133:8000"): str,
                vol.Optional(CONF_API_KEY): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
