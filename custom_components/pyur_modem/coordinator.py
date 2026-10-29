"""DataUpdateCoordinator for the Pyur Modem integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, MAX_BACKOFF_INTERVAL
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
        self._failures = 0

    async def _async_update_data(self) -> ModemData:
        try:
            data = await self.hass.async_add_executor_job(self._client.fetch)
        except AuthError as err:
            self._record_failure("auth", err)
            raise UpdateFailed(f"Authentication error: {err}") from err
        except ParseError as err:
            self._record_failure("parse", err)
            raise UpdateFailed(f"Parse error: {err}") from err
        except Exception as err:
            self._record_failure(None, err)
            raise UpdateFailed(f"Communication error: {err}") from err

        if not self._available:
            _LOGGER.info("Reconnected to Pyur modem")
            self._available = True
        self._failures = 0
        self.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
        return data

    def _record_failure(self, kind: str | None, err: Exception) -> None:
        """Log the first failure and back off so a booting or locked modem is not hammered.

        The modem web UI locks out clients after repeated logins and is not
        reachable for a while after a restart, so every failed poll doubles the
        interval (up to MAX_BACKOFF_INTERVAL) until a poll succeeds again.
        """
        if self._available:
            label = f" ({kind})" if kind else ""
            _LOGGER.warning("Lost connection to Pyur modem%s: %s", label, err)
            self._available = False
        self._failures += 1
        self.update_interval = timedelta(
            seconds=min(
                DEFAULT_SCAN_INTERVAL * 2**self._failures, MAX_BACKOFF_INTERVAL
            )
        )
