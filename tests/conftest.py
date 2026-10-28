"""Fixtures for the yt_dlp integration tests."""

from collections.abc import Generator

import pytest
from homeassistant.const import CONF_FILE_PATH
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yt_dlp.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations) -> Generator[None]:
    yield


@pytest.fixture
def download_dir(hass: HomeAssistant, tmp_path):
    hass.config.allowlist_external_dirs.add(str(tmp_path))
    return tmp_path / "downloads"


@pytest.fixture
def mock_entry(hass: HomeAssistant, download_dir) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Youtube-DLP",
        data={CONF_FILE_PATH: str(download_dir)},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    return entry
