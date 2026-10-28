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

## Downloading

### Via Developer tools -> Actions

- Search for the action "Download video" (`yt_dlp.download`).
- Enter the URL of the video to download and call the action.
- Downloads run in the background; check the progress sensor or the Home Assistant log for the result.

The action accepts these optional fields. Any other field is rejected.

| Field | Description |
| --- | --- |
| `format` | yt-dlp format selector, for example `bv*+ba/b` |
| `merge_output_format` | Container used when merging streams, for example `mp4` or `mkv` |
| `noplaylist` | Download only the video when the URL points to a video inside a playlist |
| `playlist_items` | Items to download from a playlist, for example `1-5,8` |

Files are saved in the download folder as `<title> [<id>].<ext>`. Output templates and post-processing commands are not accepted.

### Progress sensor

The sensor `sensor.youtube_dlp_downloads` shows the number of active downloads. Its attributes list each active file with `speed`, `downloaded`, `total`, and `eta`.
