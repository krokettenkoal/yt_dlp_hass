"""The yt_dlp integration."""

import asyncio
import logging
import os
import tempfile
import threading
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

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
from .helpers import check_download_dir, ensure_dir

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.SENSOR]
OUTPUT_TEMPLATE = "%(title)s [%(id)s].%(ext)s"

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
    temp_dir: str
    generation: str
    workers: dict[asyncio.Future[None], threading.Event]
    unloading: bool = False


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


class _DownloadCancelled(Exception):
    """Raised by a progress hook when its entry is unloading."""


def _make_progress_hook(
    hass: HomeAssistant,
    signal: str,
    job_id: str,
    cancel_event: threading.Event,
    stream_keys: set[str],
):

    @callback
    def _dispatch(key: str, values: dict[str, Any] | None) -> None:
        async_dispatcher_send(hass, signal, key, values)

    def progress_hook(d: dict[str, Any]) -> None:
        # Runs on yt-dlp's executor thread; only copy plain values here.
        if cancel_event.is_set():
            raise _DownloadCancelled
        info = d.get("info_dict") or {}
        stream_id = f"{info.get('id')}:{info.get('format_id')}"
        key = f"{job_id}:{stream_id}"
        stream_keys.add(key)
        values = None
        if d.get("status") == "downloading":
            values = {
                "name": os.path.basename(d.get("filename") or stream_id),
                "speed": d.get("speed"),
                "downloaded": d.get("downloaded_bytes"),
                "total": d.get("total_bytes") or d.get("total_bytes_estimate"),
                "eta": d.get("eta"),
            }
        hass.loop.call_soon_threadsafe(_dispatch, key, values)

    return progress_hook


def _run_yt_dlp(
    hass: HomeAssistant,
    signal: str,
    url: str,
    ydl_opts: dict[str, Any],
    cancel_event: threading.Event,
    stream_keys: set[str],
) -> None:
    try:
        if cancel_event.is_set():
            raise _DownloadCancelled
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    finally:
        for key in stream_keys:
            hass.loop.call_soon_threadsafe(
                async_dispatcher_send, hass, signal, key, None
            )


async def _async_download(
    hass: HomeAssistant,
    entry: YtDlpConfigEntry,
    data: YtDlpData,
    url: str,
    options: dict[str, Any],
) -> None:
    if data.unloading:
        return
    download_dir = data.download_dir
    job_id = uuid4().hex
    signal = progress_signal(entry.entry_id, data.generation)
    cancel_event = threading.Event()
    stream_keys: set[str] = set()
    ydl_opts = {
        **options,
        "paths": {
            "home": download_dir,
            "temp": data.temp_dir,
        },
        "outtmpl": OUTPUT_TEMPLATE,
        "progress_hooks": [
            _make_progress_hook(hass, signal, job_id, cancel_event, stream_keys)
        ],
        "logger": _YtDlpLogger(),
        "quiet": True,
        "noprogress": True,
        "ignoreerrors": False,
    }
    worker = hass.async_add_executor_job(
        _run_yt_dlp, hass, signal, url, ydl_opts, cancel_event, stream_keys
    )
    data.workers[worker] = cancel_event
    worker.add_done_callback(lambda future: data.workers.pop(future, None))
    try:
        await asyncio.shield(worker)
    except asyncio.CancelledError:
        cancel_event.set()
        raise
    except _DownloadCancelled:
        pass
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
    data = entry.runtime_data
    if data.unloading:
        raise ServiceValidationError("The Youtube-DLP integration is unloading")
    url = call.data["url"]
    options = {key: value for key, value in call.data.items() if key != "url"}
    entry.async_create_background_task(
        call.hass,
        _async_download(call.hass, entry, data, url, options),
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

    temp_dir = os.path.join(tempfile.gettempdir(), DOMAIN)
    try:
        await hass.async_add_executor_job(ensure_dir, temp_dir)
    except OSError as err:
        raise ConfigEntryNotReady(f"Temp folder {temp_dir} is not writable") from err

    entry.runtime_data = YtDlpData(
        download_dir=download_dir,
        temp_dir=temp_dir,
        generation=uuid4().hex,
        workers={},
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: YtDlpConfigEntry) -> bool:
    """Unload the progress sensor."""
    data = entry.runtime_data
    data.unloading = True
    workers = tuple(data.workers.items())
    for _, cancel_event in workers:
        cancel_event.set()
    if workers:
        await asyncio.gather(
            *(asyncio.shield(worker) for worker, _ in workers),
            return_exceptions=True,
        )
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unloaded:
        data.unloading = False
    return unloaded
