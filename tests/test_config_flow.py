"""Tests for the Pyur Modem config flow."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.pyur_modem.pyur_modem_lib.client import AuthError

VALID_INPUT = {
    "host": "https://192.168.100.1",
    "username": "admin",
    "password": "secret",
}

_PATCH_CLIENT = "custom_components.pyur_modem.config_flow.PyurModemClient"
_PATCH_INIT_CLIENT = "custom_components.pyur_modem.PyurModemClient"

BARE_IP_INPUT = {
    "host": "192.168.100.1",  # no https:// prefix
    "username": "admin",
    "password": "secret",
}


async def test_form_shows_on_init(hass: HomeAssistant) -> None:
    """The config flow shows a form on first load."""
    result = await hass.config_entries.flow.async_init(
        "pyur_modem", context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_successful_setup(hass: HomeAssistant, mock_client: MagicMock) -> None:
    """A valid host/user/password creates a config entry."""
    with patch(_PATCH_CLIENT, return_value=mock_client), \
         patch(_PATCH_INIT_CLIENT, return_value=mock_client):
        result = await hass.config_entries.flow.async_init(
            "pyur_modem", context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == VALID_INPUT["host"]
    assert result2["data"] == VALID_INPUT


async def test_invalid_auth(hass: HomeAssistant) -> None:
    """AuthError from login() surfaces as invalid_auth."""
    mock = MagicMock()
    mock.login.side_effect = AuthError("bad credentials")

    with patch(_PATCH_CLIENT, return_value=mock):
        result = await hass.config_entries.flow.async_init(
            "pyur_modem", context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_cannot_connect(hass: HomeAssistant) -> None:
    """OSError from login() surfaces as cannot_connect."""
    mock = MagicMock()
    mock.login.side_effect = OSError("connection refused")

    with patch(_PATCH_CLIENT, return_value=mock):
        result = await hass.config_entries.flow.async_init(
            "pyur_modem", context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_unknown_error(hass: HomeAssistant) -> None:
    """An unexpected exception surfaces as unknown."""
    mock = MagicMock()
    mock.login.side_effect = RuntimeError("unexpected")

    with patch(_PATCH_CLIENT, return_value=mock):
        result = await hass.config_entries.flow.async_init(
            "pyur_modem", context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_duplicate_entry_aborted(hass: HomeAssistant, mock_client: MagicMock) -> None:
    """Configuring the same host twice is aborted."""
    with patch(_PATCH_CLIENT, return_value=mock_client), \
         patch(_PATCH_INIT_CLIENT, return_value=mock_client):
        result = await hass.config_entries.flow.async_init(
            "pyur_modem", context={"source": "user"}
        )
        await hass.config_entries.flow.async_configure(result["flow_id"], VALID_INPUT)

    with patch(_PATCH_CLIENT, return_value=mock_client):
        result = await hass.config_entries.flow.async_init(
            "pyur_modem", context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_host_normalised_when_scheme_missing(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """Entering a bare IP without https:// is accepted and normalised."""
    with patch(_PATCH_CLIENT, return_value=mock_client), \
         patch(_PATCH_INIT_CLIENT, return_value=mock_client):
        result = await hass.config_entries.flow.async_init(
            "pyur_modem", context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], BARE_IP_INPUT
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["host"] == "https://192.168.100.1"
