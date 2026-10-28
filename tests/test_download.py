"""Tests for the download service and progress reporting."""

from unittest.mock import patch

import pytest
import voluptuous as vol
from yt_dlp.utils import DownloadError

from custom_components.yt_dlp import OUTPUT_TEMPLATE
from custom_components.yt_dlp.const import DOMAIN

SERVICE = "download"
URL = "https://www.youtube.com/watch?v=abc"
SENSOR = "sensor.youtube_dlp_downloads"
STREAM_FILE = "/downloads/Title [abc].f137.mp4"
STREAM_INFO = {"id": "abc", "format_id": "137"}


@pytest.fixture
def mock_ydl():
    with patch("custom_components.yt_dlp.YoutubeDL") as ydl_cls:
        yield ydl_cls


async def _setup(hass, entry):
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _download(hass, data):
    await hass.services.async_call(DOMAIN, SERVICE, {"url": URL, **data}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("outtmpl", "/etc/%(title)s"),
        ("postprocessors", [{"key": "Exec", "exec_cmd": "id"}]),
        ("exec_cmd", "id"),
        ("paths", {"home": "/"}),
        ("cookiefile", "/secret"),
    ],
)
async def test_service_rejects_unlisted_options(hass, mock_entry, mock_ydl, key, value):
    await _setup(hass, mock_entry)
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN, SERVICE, {"url": URL, key: value}, blocking=True
        )
    mock_ydl.assert_not_called()


async def test_service_rejects_invalid_option_value(hass, mock_entry, mock_ydl):
    await _setup(hass, mock_entry)
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE,
            {"url": URL, "merge_output_format": "../../etc"},
            blocking=True,
        )
    mock_ydl.assert_not_called()


async def test_download_passes_allowed_options(
    hass, mock_entry, mock_ydl, download_dir
):
    await _setup(hass, mock_entry)
    await _download(
        hass,
        {
            "format": "bv*+ba/b",
            "merge_output_format": "mkv",
            "noplaylist": True,
            "playlist_items": "1-3,5",
        },
    )

    opts = mock_ydl.call_args.args[0]
    assert opts["format"] == "bv*+ba/b"
    assert opts["merge_output_format"] == "mkv"
    assert opts["noplaylist"] is True
    assert opts["playlist_items"] == "1-3,5"
    assert opts["paths"]["home"] == str(download_dir)
    assert opts["outtmpl"] == OUTPUT_TEMPLATE
    assert opts["ignoreerrors"] is False
    mock_ydl.return_value.__enter__.return_value.download.assert_called_once_with([URL])


async def test_download_error_is_logged(hass, mock_entry, mock_ydl, caplog):
    await _setup(hass, mock_entry)
    mock_ydl.return_value.__enter__.return_value.download.side_effect = DownloadError(
        "boom"
    )
    await _download(hass, {})
    assert "Download failed" in caplog.text


async def test_progress_hook_updates_sensor(hass, mock_entry, mock_ydl):
    await _setup(hass, mock_entry)

    def download(urls):
        hook = mock_ydl.call_args.args[0]["progress_hooks"][0]
        hook(
            {
                "status": "downloading",
                "filename": STREAM_FILE,
                "info_dict": STREAM_INFO,
                "downloaded_bytes": 50,
                "total_bytes": 100,
                "speed": 10.0,
                "eta": 5,
            }
        )

    mock_ydl.return_value.__enter__.return_value.download.side_effect = download
    await _download(hass, {})

    state = hass.states.get(SENSOR)
    assert state.state == "1"
    assert state.attributes["Title [abc].f137.mp4"] == {
        "downloaded": 50,
        "total": 100,
        "speed": 10.0,
        "eta": 5,
    }


async def test_finished_stream_is_removed(hass, mock_entry, mock_ydl):
    await _setup(hass, mock_entry)

    def download(urls):
        hook = mock_ydl.call_args.args[0]["progress_hooks"][0]
        hook(
            {"status": "downloading", "filename": STREAM_FILE, "info_dict": STREAM_INFO}
        )
        hook({"status": "finished", "filename": STREAM_FILE, "info_dict": STREAM_INFO})

    mock_ydl.return_value.__enter__.return_value.download.side_effect = download
    await _download(hass, {})

    state = hass.states.get(SENSOR)
    assert state.state == "0"
    assert "Title [abc].f137.mp4" not in state.attributes


async def test_progress_hook_tolerates_missing_fields(hass, mock_entry, mock_ydl):
    await _setup(hass, mock_entry)

    def download(urls):
        hook = mock_ydl.call_args.args[0]["progress_hooks"][0]
        hook({"status": "downloading", "filename": STREAM_FILE, "info_dict": {}})

    mock_ydl.return_value.__enter__.return_value.download.side_effect = download
    await _download(hass, {})

    state = hass.states.get(SENSOR)
    assert state.state == "1"
    assert state.attributes["Title [abc].f137.mp4"] == {
        "downloaded": None,
        "total": None,
        "speed": None,
        "eta": None,
    }
