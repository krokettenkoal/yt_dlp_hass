"""Config flow for the yt_dlp integration."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_FILE_PATH

from .const import DOMAIN
from .helpers import check_download_dir


def _path_schema(suggested: str | None = None) -> vol.Schema:
    key = vol.Required(
        CONF_FILE_PATH,
        description={"suggested_value": suggested} if suggested else None,
    )
    return vol.Schema({key: str})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            error = await self.hass.async_add_executor_job(
                check_download_dir, self.hass, user_input[CONF_FILE_PATH]
            )
            if error is None:
                return self.async_create_entry(title="Youtube-DLP", data=user_input)
            errors["base"] = error

        return self.async_show_form(
            step_id="user", data_schema=_path_schema(), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await self.hass.async_add_executor_job(
                check_download_dir, self.hass, user_input[CONF_FILE_PATH]
            )
            if error is None:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                    reason="reconfigure_successful",
                )
            errors["base"] = error

        current = (user_input or entry.data)[CONF_FILE_PATH]
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_path_schema(current),
            errors=errors,
        )
