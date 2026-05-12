"""The Pyur Modem integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .const import DEFAULT_TIMEOUT
from .coordinator import PyurModemCoordinator
from .pyur_modem_lib import PyurModemClient

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type PyurModemConfigEntry = ConfigEntry[PyurModemCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: PyurModemConfigEntry) -> bool:
    """Set up Pyur Modem from a config entry."""
    client = PyurModemClient(
        host=entry.data[CONF_HOST],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        timeout=DEFAULT_TIMEOUT,
        verify_ssl=False,
    )

    coordinator = PyurModemCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PyurModemConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
