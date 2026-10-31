"""Tests for the yt_dlp config flow."""

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_FILE_PATH
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yt_dlp.const import DOMAIN


async def test_user_flow_creates_entry(hass, download_dir):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_FILE_PATH: str(download_dir)}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert download_dir.is_dir()

    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.state is ConfigEntryState.LOADED


async def test_user_flow_rejects_relative_path(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_FILE_PATH: "relative/downloads"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_path"}


async def test_user_flow_rejects_disallowed_path(hass, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "downloads"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_FILE_PATH: str(outside)}
    )
    assert result["errors"] == {"base": "invalid_path"}
    assert not outside.exists()


async def test_user_flow_aborts_when_configured(hass, mock_entry):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_reconfigure_updates_path_and_reloads(
    hass, mock_entry: MockConfigEntry, download_dir, tmp_path
):
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    new_dir = tmp_path / "new-downloads"
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_entry.entry_id,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_FILE_PATH: str(new_dir)}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_entry.data[CONF_FILE_PATH] == str(new_dir)
    assert mock_entry.runtime_data.download_dir == str(new_dir)
    assert new_dir.is_dir()
    assert mock_entry.state is ConfigEntryState.LOADED


async def test_options_flow_saves_defaults(hass, mock_entry):
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "restrictfilenames": False,
            "format": "ba/b",
            "merge_output_format": "mp4",
            "noplaylist": True,
            "writesubtitles": True,
            "subtitleslangs": ["de"],
            "writethumbnail": True,
            "writeinfojson": False,
            "concurrent_fragment_downloads": 4,
            "retries": 3,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_entry.options["format"] == "ba/b"
    assert mock_entry.options["subtitleslangs"] == ["de"]
    assert mock_entry.state is ConfigEntryState.LOADED
