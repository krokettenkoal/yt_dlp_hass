"""Helpers shared by the config flow and integration setup."""

import os
from pathlib import Path

from homeassistant.core import HomeAssistant


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def check_download_dir(hass: HomeAssistant, path: str) -> str | None:
    """Create the download folder if needed; return an error key on failure."""
    if not Path(path).is_absolute() or not hass.config.is_allowed_path(path):
        return "invalid_path"
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except OSError:
        return "cannot_create_folder"
    if not os.access(path, os.W_OK):
        return "cannot_create_folder"
    return None
