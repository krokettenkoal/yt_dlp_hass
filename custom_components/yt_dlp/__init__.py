"""The yt_dlp integration."""

import logging
import os
from dataclasses import dataclass
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_FILE_PATH, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import (
    ConfigEntryError,
    ConfigEntryNotReady,
    ServiceValidationError,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .const import ALLOWED_OPTIONS, DOMAIN, SERVICE_DOWNLOAD, progress_signal
from .helpers import check_download_dir

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]
OUTPUT_TEMPLATE = "%(title)s [%(id)s].%(ext)s"
TEMP_SUBDIR = ".yt_dlp_tmp"

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("url"): cv.url,
        **{
            vol.Optional(name): validator for name, validator in ALLOWED_OPTIONS.items()
        },
    },
    extra=vol.PREVENT_EXTRA,
)


@dataclass
class YtDlpData:
    download_dir: str


YtDlpConfigEntry = ConfigEntry[YtDlpData]


class _YtDlpLogger:
    """Forward yt-dlp messages to the integration logger."""

    def debug(self, msg: str) -> None:
        _LOGGER.debug(msg)

    def info(self, msg: str) -> None:
        _LOGGER.info(msg)

    def warning(self, msg: str) -> None:
        _LOGGER.warning(msg)

    def error(self, msg: str) -> None:
        _LOGGER.error(msg)


def _make_progress_hook(hass: HomeAssistant, entry_id: str):
    signal = progress_signal(entry_id)

    @callback
    def _dispatch(key: str, values: dict[str, Any] | None) -> None:
        async_dispatcher_send(hass, signal, key, values)

    def progress_hook(d: dict[str, Any]) -> None:
        # Runs on yt-dlp's executor thread; only copy plain values here.
        info = d.get("info_dict") or {}
        key = f"{info.get('id')}:{info.get('format_id')}"
        values = None
        if d.get("status") == "downloading":
            values = {
                "name": os.path.basename(d.get("filename") or key),
                "speed": d.get("speed"),
                "downloaded": d.get("downloaded_bytes"),
                "total": d.get("total_bytes") or d.get("total_bytes_estimate"),
                "eta": d.get("eta"),
            }
        hass.loop.call_soon_threadsafe(_dispatch, key, values)

    return progress_hook


def _run_yt_dlp(url: str, ydl_opts: dict[str, Any]) -> None:
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


async def _async_download(
    hass: HomeAssistant, entry: YtDlpConfigEntry, url: str, options: dict[str, Any]
) -> None:
    download_dir = entry.runtime_data.download_dir
    ydl_opts = {
        **options,
        "paths": {
            "home": download_dir,
            "temp": os.path.join(download_dir, TEMP_SUBDIR),
        },
        "outtmpl": OUTPUT_TEMPLATE,
        "progress_hooks": [_make_progress_hook(hass, entry.entry_id)],
        "logger": _YtDlpLogger(),
        "quiet": True,
        "noprogress": True,
        "ignoreerrors": False,
    }
    try:
        await hass.async_add_executor_job(_run_yt_dlp, url, ydl_opts)
    except DownloadError as err:
        _LOGGER.error("Download failed for %s: %s", url, err)
    else:
        _LOGGER.info("Download finished: %s", url)


async def _async_handle_download(call: ServiceCall) -> None:
    entries: list[YtDlpConfigEntry] = call.hass.config_entries.async_loaded_entries(
        DOMAIN
    )
    if not entries:
        raise ServiceValidationError("The Youtube-DLP integration is not set up")
    entry = entries[0]
    url = call.data["url"]
    options = {key: value for key, value in call.data.items() if key != "url"}
    entry.async_create_background_task(
        call.hass,
        _async_download(call.hass, entry, url, options),
        name=f"{DOMAIN} download {url}",
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the download service."""
    hass.services.async_register(
        DOMAIN, SERVICE_DOWNLOAD, _async_handle_download, schema=SERVICE_SCHEMA
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: YtDlpConfigEntry) -> bool:
    """Prepare the download folder and set up the progress sensor."""
    download_dir = entry.data[CONF_FILE_PATH]
    error = await hass.async_add_executor_job(check_download_dir, hass, download_dir)
    if error == "invalid_path":
        raise ConfigEntryError(f"Download folder {download_dir} is not allowed")
    if error:
        raise ConfigEntryNotReady(f"Download folder {download_dir} is not writable")

    entry.runtime_data = YtDlpData(download_dir=download_dir)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: YtDlpConfigEntry) -> bool:
    """Unload the progress sensor."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
