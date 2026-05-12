"""Config flow for the Pyur Modem integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .pyur_modem_lib import PyurModemClient
from .pyur_modem_lib.client import AuthError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


def _normalize_host(host: str) -> str:
    """Ensure the host has an https:// scheme and no trailing slash."""
    host = host.strip()
    if not host.startswith(("http://", "https://")):
        host = f"https://{host}"
    return host.rstrip("/")


async def _validate_input(hass: HomeAssistant, data: dict) -> None:
    """Try to connect and authenticate. Raises on failure."""
    client = PyurModemClient(
        host=data[CONF_HOST],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        timeout=10,
        verify_ssl=False,
    )
    await hass.async_add_executor_job(client.login)
    try:
        await hass.async_add_executor_job(client.logout)
    except Exception:  # noqa: BLE001
        pass


class PyurModemConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pyur Modem."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_HOST] = _normalize_host(user_input[CONF_HOST])
            try:
                await _validate_input(self.hass, user_input)
            except AuthError:
                errors["base"] = "invalid_auth"
            except OSError as err:
                _LOGGER.exception("Cannot connect to modem: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during config flow: %s", err)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_HOST],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict) -> ConfigFlowResult:
        """Triggered when credentials become invalid — re-prompt for password."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            data = {**reauth_entry.data, **user_input}
            try:
                await _validate_input(self.hass, data)
            except AuthError:
                errors["base"] = "invalid_auth"
            except OSError as err:
                _LOGGER.exception("Cannot connect to modem during reauth: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during reauth: %s", err)
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(reauth_entry, data=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=reauth_entry.data.get(CONF_USERNAME, ""),
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
            description_placeholders={"host": reauth_entry.data[CONF_HOST]},
        )
