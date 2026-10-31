# yt-dlp Video Downloader for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Latest release](https://img.shields.io/github/v/release/krokettenkoal/yt_dlp_hass)](https://github.com/krokettenkoal/yt_dlp_hass/releases)
[![License: GPL-3.0](https://img.shields.io/github/license/krokettenkoal/yt_dlp_hass)](LICENSE)

Download videos with [yt-dlp](https://github.com/yt-dlp/yt-dlp) straight from Home Assistant. Call one action with a URL, and the video lands in a folder on your Home Assistant host. A sensor shows active downloads and their progress.

## Table of contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Downloading](#downloading)
- [Download options](#download-options)
- [Progress sensor](#progress-sensor)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features

- Download a video or playlist with a single action: `yt_dlp.download`.
- Best quality by default, with presets for 1080p, 720p and audio-only.
- Clean file names, with quotes and special characters removed.
- Optional subtitles, thumbnail, and video metadata files.
- Downloads run in the background, so Home Assistant stays responsive.
- A progress sensor shows active downloads, speed, and time remaining.

## Installation

### Option 1: HACS (recommended)

1. Open [HACS](https://hacs.xyz/) in Home Assistant and go to **Integrations**.
2. Open the menu (⋮) and choose **Custom repositories**.
3. Add `https://github.com/krokettenkoal/yt_dlp_hass` with the category **Integration**.
4. Search for **yt-dlp Video Downloader**, open it, and choose **Download**.
5. Restart Home Assistant.

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=krokettenkoal&repository=yt_dlp_hass&category=integration)

### Option 2: Manual

1. Download or clone this repository.
2. Copy the `custom_components/yt_dlp` folder into the `custom_components` folder of your Home Assistant config directory:

   ```text
   <config directory>/custom_components/yt_dlp/
   ```

3. Restart Home Assistant.

> [!IMPORTANT]
> A restart is required after installing or updating the integration. Home Assistant loads custom integrations only at startup.

## Configuration

1. Go to **Settings → Devices & services** and select **Add integration**.
2. Search for **yt-dlp Video Downloader** and select it.

   [![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=yt_dlp)

3. Enter the **absolute path** of the download folder, for example `/media/youtube`.
4. Select **Submit**.

The folder is created if it does not exist. To change it later, open the integration and select **Reconfigure**.

> [!IMPORTANT]
> The download folder must be inside your config directory, or listed in `allowlist_external_dirs` in `configuration.yaml`. Otherwise the setup fails with "Path must be absolute and inside an allowed directory":
>
> ```yaml
> homeassistant:
>   allowlist_external_dirs:
>     - /media/youtube
> ```
>
> Restart Home Assistant after changing `configuration.yaml`.

> [!NOTE]
> Only one download folder can be configured. Partial downloads are kept in the system temporary directory until each download finishes.

## Downloading

### From Developer tools → Actions

1. Go to **Developer tools → Actions** and search for **Download video** (`yt_dlp.download`).
2. Enter the `url` of the video or playlist.
3. Optionally set any of the [download options](#download-options). Anything left out uses your saved defaults.
4. Select **Perform action**.

The download runs in the background. Check the [progress sensor](#progress-sensor) or the Home Assistant log for the result.

### From an automation

```yaml
action: yt_dlp.download
data:
  url: https://www.youtube.com/watch?v=1234567890
  format: bv*[height<=720]+ba/b[height<=720]
```

> [!TIP]
> To change the defaults for every download, open the integration and select **Configure**. Options set in a service call override the defaults for that call only.

## Download options

Set defaults under **Settings → Devices & services → yt-dlp Video Downloader → Configure**. Each option can also be set in a `yt_dlp.download` call. Changes apply to the next download, and running downloads are not affected.

| Option | Default | Description |
| --- | --- | --- |
| `restrictfilenames` | on | Replace spaces with underscores and remove quotes, dashes and other special characters. Accents become plain letters. |
| `format` | `bv*+ba/b` (best quality) | yt-dlp format selector. Presets for best, 1080p, 720p and audio-only are offered, or enter your own. |
| `merge_output_format` | `mkv` | Container used when merging video and audio, for example `mp4` or `mkv`. |
| `noplaylist` | off | If the URL points to a video inside a playlist, download only that video. |
| `playlist_items` | (none) | Items to download from a playlist, for example `1-5,8`. Service call only. |
| `writesubtitles` | off | Save subtitles as separate files. |
| `subtitleslangs` | `en` | Subtitle languages, for example `en` or `de`. |
| `writethumbnail` | off | Save the thumbnail as a separate image file. |
| `writeinfojson` | off | Save the video metadata as a separate `.info.json` file. |
| `concurrent_fragment_downloads` | 1 | Fragments downloaded at the same time (1–16). |
| `retries` | 10 | Retries for a failed download (0–50). |

Files are saved in the download folder as `<title>_<id>.<ext>`, for example `My_Video_abc123.mp4`.

> [!TIP]
> Keep **Restrict filenames** on. It removes quotes and en/em dashes from titles, so file names work everywhere, including SMB shares.

> [!WARNING]
> A title with no Latin letters, such as a Japanese title, becomes an underscore, so the file is named `__<id>.<ext>`. Options that run post-processing commands or change the output template are not available.

## Progress sensor

The sensor `sensor.yt_dlp_video_downloader_downloads` shows how many downloads are active. Its attributes list each file with:

- `speed`: current download speed
- `downloaded`: bytes downloaded so far
- `total`: total size, if known
- `eta`: estimated time remaining, in seconds

The sensor is part of the **yt-dlp Video Downloader** device.

> [!NOTE]
> Installations set up before the rename keep the old entity ID `sensor.youtube_dlp_downloads`, because Home Assistant keeps the ID of existing entities. To use the new ID, rename the entity under **Settings → Entities**.

## Troubleshooting

**The download folder is not writable or not allowed.**
Check that the folder is absolute and inside your config directory or `allowlist_external_dirs`. Check the permissions of the folder for the user that runs Home Assistant.

**Partial files are left in a folder, or a file cannot be deleted.**
A download that was interrupted can leave a partial file behind. If a file is locked, it's usually still open by a running download. Restart Home Assistant, then try again.

> [!CAUTION]
> Avoid deleting files with `sudo` while a download is running. The file may still be in use, and the deletion can hide the real cause.

**Check the log.**
Errors from yt-dlp appear in the Home Assistant log under the `custom_components.yt_dlp` logger. For more detail, add this to `configuration.yaml` and restart:

```yaml
logger:
  logs:
    custom_components.yt_dlp: debug
```

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE). yt-dlp is a separate project with its own license.
