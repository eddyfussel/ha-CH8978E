"""Tests for the coordinator's failure back-off."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.pyur_modem.const import (
    DEFAULT_SCAN_INTERVAL,
    MAX_BACKOFF_INTERVAL,
)
from custom_components.pyur_modem.coordinator import PyurModemCoordinator
from custom_components.pyur_modem.pyur_modem_lib.client import AuthError


async def test_backoff_doubles_and_resets(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """Failed polls lengthen the interval up to the cap; a success resets it."""
    coordinator = PyurModemCoordinator(hass, mock_client)
    good = mock_client.fetch.return_value
    mock_client.fetch.side_effect = AuthError("locked out")

    intervals = []
    for _ in range(6):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        intervals.append(coordinator.update_interval.total_seconds())

    assert intervals[0] == DEFAULT_SCAN_INTERVAL * 2
    assert intervals[1] == DEFAULT_SCAN_INTERVAL * 4
    assert intervals[-1] == MAX_BACKOFF_INTERVAL

    mock_client.fetch.side_effect = None
    mock_client.fetch.return_value = good
    assert await coordinator._async_update_data() is good
    assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)
