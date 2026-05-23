from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KitchenIOApiError, KitchenIOClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class KitchenIOCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Fetch KitchenIO stock on a regular interval."""

    def __init__(self, hass: HomeAssistant, client: KitchenIOClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            return await self.client.async_stock()
        except KitchenIOApiError as exc:
            raise UpdateFailed(str(exc)) from exc
