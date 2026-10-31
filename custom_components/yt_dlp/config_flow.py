"""Config flow for the yt_dlp integration."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_FILE_PATH
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DEFAULT_OPTIONS, DOMAIN
from .helpers import check_download_dir

FORMAT_PRESETS = [
    {"value": "bv*+ba/b", "label": "Best quality"},
    {"value": "bv*[height<=1080]+ba/b[height<=1080]", "label": "Up to 1080p"},
    {"value": "bv*[height<=720]+ba/b[height<=720]", "label": "Up to 720p"},
    {"value": "ba/b", "label": "Audio only"},
]


def _path_schema(suggested: str | None = None) -> vol.Schema:
    key = vol.Required(
        CONF_FILE_PATH,
        description={"suggested_value": suggested} if suggested else None,
    )
    return vol.Schema({key: str})


def _options_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("restrictfilenames"): selector.BooleanSelector(),
            vol.Required("format"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=FORMAT_PRESETS, custom_value=True)
            ),
            vol.Required("merge_output_format"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["mkv", "mp4", "webm"], custom_value=True
                )
            ),
            vol.Required("noplaylist"): selector.BooleanSelector(),
            vol.Required("writesubtitles"): selector.BooleanSelector(),
            vol.Required("subtitleslangs"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["en", "de", "fr", "es", "ja"],
                    multiple=True,
                    custom_value=True,
                )
            ),
            vol.Required("writethumbnail"): selector.BooleanSelector(),
            vol.Required("writeinfojson"): selector.BooleanSelector(),
            vol.Required("concurrent_fragment_downloads"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=16, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required("retries"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=50, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return OptionsFlowHandler()

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
                return self.async_create_entry(
                    title="yt-dlp Video Downloader", data=user_input
                )
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


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Default download options. Changes apply to the next download."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _options_schema(), {**DEFAULT_OPTIONS, **self.config_entry.options}
            ),
        )
