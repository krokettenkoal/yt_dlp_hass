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
    "restrictfilenames": cv.boolean,
    "format": vol.All(cv.string, vol.Length(max=256)),
    "merge_output_format": vol.All(
        cv.string, cv.matches_regex(r"^[a-z0-9]+(/[a-z0-9]+)*$")
    ),
    "noplaylist": cv.boolean,
    "playlist_items": vol.All(cv.string, _validate_playlist_items),
    "writesubtitles": cv.boolean,
    "subtitleslangs": vol.All(cv.ensure_list, [cv.string]),
    "writethumbnail": cv.boolean,
    "writeinfojson": cv.boolean,
    "concurrent_fragment_downloads": vol.All(vol.Coerce(int), vol.Range(min=1, max=16)),
    "retries": vol.All(vol.Coerce(int), vol.Range(min=0, max=50)),
}

DEFAULT_OPTIONS = {
    "restrictfilenames": True,
    "format": "bv*+ba/b",
    "merge_output_format": "mkv",
    "noplaylist": False,
    "writesubtitles": False,
    "subtitleslangs": ["en"],
    "writethumbnail": False,
    "writeinfojson": False,
    "concurrent_fragment_downloads": 1,
    "retries": 10,
}


def progress_signal(entry_id: str, generation: str) -> str:
    return f"{DOMAIN}_progress_{entry_id}_{generation}"
