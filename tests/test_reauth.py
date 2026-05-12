"""Tests for the reauthentication config flow."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.pyur_modem.pyur_modem_lib.client import AuthError

_PATCH_CLIENT = "custom_components.pyur_modem.config_flow.PyurModemClient"
_PATCH_INIT_CLIENT = "custom_components.pyur_modem.PyurModemClient"

VALID_INPUT = {
    "host": "https://192.168.100.1",
    "username": "admin",
    "password": "secret",
}


@pytest.fixture
async def config_entry(hass: HomeAssistant, mock_client: MagicMock):
    """Create a config entry for reauth tests."""
    with patch(_PATCH_CLIENT, return_value=mock_client), \
         patch(_PATCH_INIT_CLIENT, return_value=mock_client):
        result = await hass.config_entries.flow.async_init(
            "pyur_modem", context={"source": "user"}
        )
        await hass.config_entries.flow.async_configure(result["flow_id"], VALID_INPUT)
        await hass.async_block_till_done()

    entries = hass.config_entries.async_entries("pyur_modem")
    assert entries
    return entries[0]


async def test_reauth_shows_form(hass: HomeAssistant, config_entry) -> None:
    """Reauth flow shows a form prompting for new credentials."""
    result = await hass.config_entries.flow.async_init(
        "pyur_modem",
        context={"source": SOURCE_REAUTH, "entry_id": config_entry.entry_id},
        data=config_entry.data,
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


async def test_reauth_success(
    hass: HomeAssistant, config_entry, mock_client: MagicMock
) -> None:
    """Successful reauth updates the entry and reloads."""
    result = await hass.config_entries.flow.async_init(
        "pyur_modem",
        context={"source": SOURCE_REAUTH, "entry_id": config_entry.entry_id},
        data=config_entry.data,
    )
    with patch(_PATCH_CLIENT, return_value=mock_client), \
         patch(_PATCH_INIT_CLIENT, return_value=mock_client):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "admin", "password": "new_secret"},
        )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert config_entry.data["password"] == "new_secret"


async def test_reauth_invalid_auth(hass: HomeAssistant, config_entry) -> None:
    """Wrong credentials during reauth surface as invalid_auth error."""
    bad_client = MagicMock()
    bad_client.login.side_effect = AuthError("bad creds")

    result = await hass.config_entries.flow.async_init(
        "pyur_modem",
        context={"source": SOURCE_REAUTH, "entry_id": config_entry.entry_id},
        data=config_entry.data,
    )
    with patch(_PATCH_CLIENT, return_value=bad_client):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "admin", "password": "wrong"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_reauth_cannot_connect(hass: HomeAssistant, config_entry) -> None:
    """OSError during reauth surfaces as cannot_connect."""
    bad_client = MagicMock()
    bad_client.login.side_effect = OSError("connection refused")

    result = await hass.config_entries.flow.async_init(
        "pyur_modem",
        context={"source": SOURCE_REAUTH, "entry_id": config_entry.entry_id},
        data=config_entry.data,
    )
    with patch(_PATCH_CLIENT, return_value=bad_client):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "admin", "password": "secret"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
