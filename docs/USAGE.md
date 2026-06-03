# Usage Guide

## Start The App

Run from source:

```powershell
python main.py
```

Or download a packaged Windows build from GitHub Releases when available.

## Download Media

1. Paste a supported media URL into the Downloader tab.
2. Wait for the app to fetch title, thumbnail, and available metadata.
3. Choose video or audio mode.
4. Select resolution and subtitle options when available.
5. Choose the save folder.
6. Press Download to add the item to the queue.

## Duplicate Handling

Media Fetch AIA can handle files that already exist in the output folder:

- Ask before overwriting.
- Auto-rename the new file.
- Overwrite the existing file.
- Skip the download.

## History

The History tab keeps local records of completed downloads. It supports search, thumbnail previews, and quick access to downloaded files.

## Settings Location

Settings and history are stored locally:

```text
%USERPROFILE%\.media_fetch_aia
```

Older settings from `%USERPROFILE%\.new_youtube_downloader` are copied into the new app folder when available.
