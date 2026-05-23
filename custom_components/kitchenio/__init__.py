from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KitchenIOClient
from .const import CONF_API_KEY, CONF_URL, DOMAIN, PLATFORMS
from .coordinator import KitchenIOCoordinator
from .services import async_setup_services, async_unload_services
from .shopping_sync import KitchenIOShoppingSync


KitchenIOConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: KitchenIOConfigEntry) -> bool:
    """Set up KitchenIO from a config entry."""
    session = async_get_clientsession(hass)
    client = KitchenIOClient(
        session=session,
        url=entry.data[CONF_URL],
        api_key=entry.data.get(CONF_API_KEY),
    )
    coordinator = KitchenIOCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()
    sync = KitchenIOShoppingSync(hass, coordinator)
    await sync.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coordinator, "sync": sync}
    await async_setup_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KitchenIOConfigEntry) -> bool:
    """Unload KitchenIO."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        await entry_data["sync"].async_stop()
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)
    return unload_ok
