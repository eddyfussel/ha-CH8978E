"""DataUpdateCoordinator for the Pyur Modem integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .pyur_modem_lib import PyurModemClient
from .pyur_modem_lib.client import AuthError, ModemData, ParseError

_LOGGER = logging.getLogger(__name__)


class PyurModemCoordinator(DataUpdateCoordinator[ModemData]):
    """Polls the modem every DEFAULT_SCAN_INTERVAL seconds."""

    def __init__(self, hass: HomeAssistant, client: PyurModemClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._client = client
        self._available = True

    async def _async_update_data(self) -> ModemData:
        try:
            data = await self.hass.async_add_executor_job(self._client.fetch)
        except AuthError as err:
            if self._available:
                _LOGGER.warning("Lost connection to Pyur modem (auth): %s", err)
                self._available = False
            raise UpdateFailed(f"Authentication error: {err}") from err
        except ParseError as err:
            if self._available:
                _LOGGER.warning("Lost connection to Pyur modem (parse): %s", err)
                self._available = False
            raise UpdateFailed(f"Parse error: {err}") from err
        except Exception as err:
            if self._available:
                _LOGGER.warning("Lost connection to Pyur modem: %s", err)
                self._available = False
            raise UpdateFailed(f"Communication error: {err}") from err
        else:
            if not self._available:
                _LOGGER.info("Reconnected to Pyur modem")
                self._available = True
            return data
