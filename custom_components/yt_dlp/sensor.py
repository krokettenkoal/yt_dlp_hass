"""Sensor reporting active yt-dlp downloads."""

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import YtDlpConfigEntry
from .const import DOMAIN, progress_signal


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YtDlpConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([DownloadsSensor(entry)])


class DownloadsSensor(SensorEntity):
    """Number of active downloads, with per-stream progress as attributes."""

    _attr_has_entity_name = True
    _attr_translation_key = "downloads"
    _attr_should_poll = False

    def __init__(self, entry: YtDlpConfigEntry) -> None:
        self._entry_id = entry.entry_id
        self._generation = entry.runtime_data.generation
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Youtube-DLP",
            entry_type=DeviceEntryType.SERVICE,
        )
        self._streams: dict[str, dict[str, Any]] = {}

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                progress_signal(self._entry_id, self._generation),
                self._async_on_progress,
            )
        )

    @callback
    def _async_on_progress(self, key: str, values: dict[str, Any] | None) -> None:
        if values is None:
            self._streams.pop(key, None)
        else:
            self._streams[key] = values
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        return len(self._streams)

    @property
    def extra_state_attributes(self) -> dict[str, dict[str, Any]]:
        return {
            f"{stream['name']} ({key})": {
                k: v for k, v in stream.items() if k != "name"
            }
            for key, stream in self._streams.items()
        }
