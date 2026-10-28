"""Constants for the yt_dlp integration."""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

DOMAIN = "yt_dlp"
SERVICE_DOWNLOAD = "download"

ALLOWED_OPTIONS = {
    "format": vol.All(cv.string, vol.Length(max=256)),
    "merge_output_format": vol.All(
        cv.string, cv.matches_regex(r"^[a-z0-9]+(/[a-z0-9]+)*$")
    ),
    "noplaylist": cv.boolean,
    "playlist_items": vol.All(cv.string, cv.matches_regex(r"^[0-9,:\-\s]+$")),
}


def progress_signal(entry_id: str) -> str:
    return f"{DOMAIN}_progress_{entry_id}"
