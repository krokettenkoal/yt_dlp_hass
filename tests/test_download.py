"""Tests for the download service and progress reporting."""

import asyncio
import threading
from unittest.mock import patch

import pytest
import voluptuous as vol
from homeassistant.helpers.dispatcher import async_dispatcher_send
from yt_dlp.utils import DownloadError

from custom_components.yt_dlp import (
    OUTPUT_TEMPLATE,
    _async_download,
    _make_progress_hook,
)
from custom_components.yt_dlp.const import DOMAIN, progress_signal

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


async def test_service_rejects_invalid_playlist_items(hass, mock_entry, mock_ydl):
    await _setup(hass, mock_entry)
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN, SERVICE, {"url": URL, "playlist_items": "1,,2"}, blocking=True
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


async def test_failed_download_cleans_up_progress(hass, mock_entry, mock_ydl):
    await _setup(hass, mock_entry)

    def download(urls):
        hook = mock_ydl.call_args.args[0]["progress_hooks"][0]
        hook(
            {
                "status": "downloading",
                "filename": STREAM_FILE,
                "info_dict": STREAM_INFO,
            }
        )
        raise DownloadError("boom")

    mock_ydl.return_value.__enter__.return_value.download.side_effect = download
    await _download(hass, {})

    state = hass.states.get(SENSOR)
    assert state.state == "0"
    assert not any(key.startswith("Title [abc].f137.mp4 (") for key in state.attributes)


async def test_progress_hook_updates_sensor(hass, mock_entry):
    await _setup(hass, mock_entry)
    hook = _make_progress_hook(
        hass,
        progress_signal(mock_entry.entry_id, mock_entry.runtime_data.generation),
        "job",
        threading.Event(),
        set(),
    )
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
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR)
    assert state.state == "1"
    stream_key = next(
        key for key in state.attributes if key.startswith("Title [abc].f137.mp4 (")
    )
    assert state.attributes[stream_key] == {
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
    assert not any(key.startswith("Title [abc].f137.mp4 (") for key in state.attributes)


async def test_progress_hook_tolerates_missing_fields(hass, mock_entry):
    await _setup(hass, mock_entry)
    hook = _make_progress_hook(
        hass,
        progress_signal(mock_entry.entry_id, mock_entry.runtime_data.generation),
        "job",
        threading.Event(),
        set(),
    )
    hook({"status": "downloading", "filename": STREAM_FILE, "info_dict": {}})
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR)
    assert state.state == "1"
    stream_key = next(
        key for key in state.attributes if key.startswith("Title [abc].f137.mp4 (")
    )
    assert state.attributes[stream_key] == {
        "downloaded": None,
        "total": None,
        "speed": None,
        "eta": None,
    }


async def test_overlapping_downloads_have_distinct_streams(hass, mock_entry):
    await _setup(hass, mock_entry)
    data = mock_entry.runtime_data
    signal = progress_signal(mock_entry.entry_id, data.generation)
    cancel_event = threading.Event()
    stream_keys = [set(), set()]
    hooks = [
        _make_progress_hook(hass, signal, f"job-{index}", cancel_event, keys)
        for index, keys in enumerate(stream_keys)
    ]

    for hook in hooks:
        hook(
            {
                "status": "downloading",
                "filename": STREAM_FILE,
                "info_dict": STREAM_INFO,
                "downloaded_bytes": 50,
                "total_bytes": 100,
            }
        )
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR)
    assert state.state == "2"
    assert (
        len(
            [
                key
                for key in state.attributes
                if key.startswith("Title [abc].f137.mp4 (")
            ]
        )
        == 2
    )
    assert stream_keys[0].isdisjoint(stream_keys[1])

    hooks[0]({"status": "finished", "filename": STREAM_FILE, "info_dict": STREAM_INFO})
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "1"

    hooks[1]({"status": "finished", "filename": STREAM_FILE, "info_dict": STREAM_INFO})
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "0"


async def test_unload_cancels_worker_and_isolates_generation(
    hass, mock_entry, mock_ydl
):
    await _setup(hass, mock_entry)
    old_data = mock_entry.runtime_data
    old_generation = old_data.generation
    started = threading.Event()
    continue_download = threading.Event()
    finished = threading.Event()

    def download(urls):
        hook = mock_ydl.call_args.args[0]["progress_hooks"][0]
        hook(
            {
                "status": "downloading",
                "filename": STREAM_FILE,
                "info_dict": STREAM_INFO,
            }
        )
        started.set()
        continue_download.wait(5)
        try:
            hook(
                {
                    "status": "downloading",
                    "filename": STREAM_FILE,
                    "info_dict": STREAM_INFO,
                }
            )
        finally:
            finished.set()

    mock_ydl.return_value.__enter__.return_value.download.side_effect = download
    await hass.services.async_call(DOMAIN, SERVICE, {"url": URL}, blocking=True)
    assert await hass.async_add_executor_job(started.wait, 1)

    unload = asyncio.create_task(hass.config_entries.async_unload(mock_entry.entry_id))
    await asyncio.sleep(0)
    continue_download.set()
    assert await unload
    assert finished.is_set()

    await hass.config_entries.async_setup(mock_entry.entry_id)
    new_generation = mock_entry.runtime_data.generation
    assert old_generation != new_generation
    await _async_download(hass, mock_entry, old_data, URL, {})
    assert mock_ydl.call_count == 1
    async_dispatcher_send(
        hass,
        progress_signal(mock_entry.entry_id, old_generation),
        "old-job:abc:137",
        {"name": "stale.mp4", "downloaded": 1},
    )
    assert hass.states.get(SENSOR).state == "0"
