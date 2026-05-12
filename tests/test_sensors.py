"""Integration-level tests: load the full entry and verify all entity states."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from .conftest import MOCK_MODEM_DATA

_PATCH_CLIENT = "custom_components.pyur_modem.PyurModemClient"

VALID_ENTRY_DATA = {
    "host": "https://192.168.100.1",
    "username": "admin",
    "password": "secret",
}


@pytest.fixture
async def loaded_entry(hass: HomeAssistant, mock_client: MagicMock):
    """Set up the pyur_modem integration and return the config entry."""
    with patch(_PATCH_CLIENT, return_value=mock_client):
        result = await hass.config_entries.flow.async_init(
            "pyur_modem", context={"source": "user"}
        )
        with patch("custom_components.pyur_modem.config_flow.PyurModemClient", return_value=mock_client):
            await hass.config_entries.flow.async_configure(result["flow_id"], VALID_ENTRY_DATA)
        await hass.async_block_till_done()

    entries = hass.config_entries.async_entries("pyur_modem")
    assert entries, "config entry was not created"
    return entries[0]


async def test_sensor_states_are_valid(hass: HomeAssistant, loaded_entry) -> None:
    """All sensor entities must have a valid, writable state (no HA ValueError)."""
    expected = {
        "sensor.pyur_ch8978e_modem_cm_status": MOCK_MODEM_DATA.cm_status,
        "sensor.pyur_ch8978e_modem_docsis_version": MOCK_MODEM_DATA.docsis_version,
        "sensor.pyur_ch8978e_modem_device_mode": MOCK_MODEM_DATA.device_mode,
        "sensor.pyur_ch8978e_modem_firmware_version": MOCK_MODEM_DATA.firmware_version,
        "sensor.pyur_ch8978e_modem_uptime": str(MOCK_MODEM_DATA.uptime_seconds),
    }
    for entity_id, expected_state in expected.items():
        state = hass.states.get(entity_id)
        assert state is not None, f"{entity_id} not found in state machine"
        assert state.state == expected_state, f"{entity_id}: expected {expected_state!r}, got {state.state!r}"


async def test_modem_time_sensor_is_timezone_aware(hass: HomeAssistant, loaded_entry) -> None:
    """The modem_time sensor must provide a timezone-aware datetime (HA 2026.5 requirement)."""
    state = hass.states.get("sensor.pyur_ch8978e_modem_modem_time")
    assert state is not None, "modem_time sensor not found"
    # HA serialises timezone-aware timestamps to ISO 8601 with offset, e.g. "2026-05-12T10:00:00+00:00"
    assert "+" in state.state or state.state.endswith("Z"), (
        f"modem_time state is not timezone-aware: {state.state!r}"
    )


async def test_operational_binary_sensor(hass: HomeAssistant, loaded_entry) -> None:
    """The operational binary sensor must be 'on' when cm_status is OPERATIONAL."""
    state = hass.states.get("binary_sensor.pyur_ch8978e_modem_operational")
    assert state is not None, "operational binary sensor not found"
    assert state.state == "on"
