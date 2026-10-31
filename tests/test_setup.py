"""Tests for the yt_dlp setup and unload."""

import tempfile
from pathlib import Path

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_FILE_PATH
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yt_dlp.const import DOMAIN


async def test_setup_and_unload(hass, mock_entry):
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.yt_dlp_video_downloader_downloads") is not None
    assert Path(mock_entry.runtime_data.temp_dir).is_dir()
    assert (
        Path(mock_entry.runtime_data.temp_dir) == Path(tempfile.gettempdir()) / DOMAIN
    )

    await hass.config_entries.async_unload(mock_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_error_when_path_not_allowed(hass, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "downloads"
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_FILE_PATH: str(outside)}, unique_id=DOMAIN
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
