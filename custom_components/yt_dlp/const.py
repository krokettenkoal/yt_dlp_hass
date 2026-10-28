"""Constants for the yt_dlp integration."""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from yt_dlp.utils import PlaylistEntries

DOMAIN = "yt_dlp"
SERVICE_DOWNLOAD = "download"


def _validate_playlist_items(value: str) -> str:
    try:
        tuple(PlaylistEntries.parse_playlist_items(value))
    except ValueError as err:
        raise vol.Invalid(str(err)) from err
    return value


ALLOWED_OPTIONS = {
    "format": vol.All(cv.string, vol.Length(max=256)),
    "merge_output_format": vol.All(
        cv.string, cv.matches_regex(r"^[a-z0-9]+(/[a-z0-9]+)*$")
    ),
    "noplaylist": cv.boolean,
    "playlist_items": vol.All(cv.string, _validate_playlist_items),
}


def progress_signal(entry_id: str, generation: str) -> str:
    return f"{DOMAIN}_progress_{entry_id}_{generation}"
