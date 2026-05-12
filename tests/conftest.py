"""Shared test fixtures for the Pyur Modem integration."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.pyur_modem.pyur_modem_lib.client import ModemData

MOCK_MAC = "AA:BB:CC:DD:EE:FF"

MOCK_MODEM_DATA = ModemData(
    cm_status="OPERATIONAL",
    network_access=True,
    docsis_version="3.1",
    device_mode="Router",
    mac_address=MOCK_MAC,
    serial_number="SN123456",
    firmware_version="CH8978E-7.24.310.51-NOSH",
    hardware_version="2.0",
    current_time=datetime(2026, 5, 12, 10, 0, 0, tzinfo=UTC),
    uptime_seconds=86400,
    uptime_string="1 Tage 0h: 0m: 0s",
    raw={},
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: HomeAssistant,
) -> None:
    """Enable custom integrations for all tests in this package."""


@pytest.fixture
def mock_client() -> MagicMock:
    """Return a mock PyurModemClient that returns MOCK_MODEM_DATA on fetch()."""
    client = MagicMock()
    client.login.return_value = None
    client.fetch.return_value = MOCK_MODEM_DATA
    client.logout.return_value = None
    return client
