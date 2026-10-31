# Integration to use YT-DLP within Home Assistant

Downloads videos with [yt-dlp](https://github.com/yt-dlp/yt-dlp) into a folder on your Home Assistant host and reports active downloads through a sensor.

## Installation

### Manually

Clone or download this repository and copy the "yt_dlp" directory to your "custom_components" directory in your config directory

```<config directory>/custom_components/yt_dlp/...```

## HACS

- Add Custom Repositories

```text
Repository: https://github.com/krokettenkoal/yt_dlp_hass
Category: Integration
```

## Configuration

### Configuration via the "Settings -> Devices & services" section of the Home Assistant UI

- Add the integration labeled "Youtube-DLP".
- Enter the absolute path of the download folder.

The folder must be inside an allowed directory (by default, Home Assistant's `www` and media directories), or explicitly listed in `allowlist_external_dirs` in `configuration.yaml`:

```yaml
homeassistant:
  allowlist_external_dirs:
    - /media/youtube
```

The folder is created if it does not exist. To change it later, use the integration's "Reconfigure" option.

Partial downloads are kept in a `yt_dlp` folder in the system temporary directory until each download finishes. If the system clears that folder, for example on reboot, an interrupted download starts over.

## Downloading

### Via Developer tools -> Actions

- Search for the action "Download video" (`yt_dlp.download`).
- Enter the URL of the video to download and call the action.
- Downloads run in the background; check the progress sensor or the Home Assistant log for the result.

The action accepts these optional fields. Any field left out uses the value from the integration's Configure dialog. Any other field is rejected.

| Field | Default | Description |
| --- | --- | --- |
| `restrictfilenames` | on | Replace spaces with underscores and remove quotes, dashes and other special characters. Accents become plain letters. |
| `format` | `bv*+ba/b` (best quality) | yt-dlp format selector. Presets for 1080p, 720p and audio only are offered in the form. |
| `merge_output_format` | `mkv` | Container used when merging video and audio streams, for example `mp4` or `mkv` |
| `noplaylist` | off | Download only the video when the URL points to a video inside a playlist |
| `playlist_items` | (none) | Items to download from a playlist, for example `1-5,8` |
| `writesubtitles` | off | Save subtitles as separate files |
| `subtitleslangs` | `en` | Subtitle languages, for example `en` or `de` |
| `writethumbnail` | off | Save the thumbnail as a separate image file |
| `writeinfojson` | off | Save the video metadata as a separate `.info.json` file |
| `concurrent_fragment_downloads` | 1 | Fragments downloaded at the same time (1–16) |
| `retries` | 10 | Retries for a failed download (0–50) |

Files are saved in the download folder as `<title>_<id>.<ext>`, for example `My_Video_abc123.mp4`. Output templates and post-processing commands are not accepted.

A title with no Latin letters, for example a Japanese title, becomes an underscore, so the file is named `__<id>.<ext>`.

Changes in the Configure dialog apply to the next download. Running downloads are not affected.

### Progress sensor

The sensor `sensor.youtube_dlp_downloads` shows the number of active downloads. Its attributes list each active file with `speed`, `downloaded`, `total`, and `eta`.
