# FAQ

## Why are compiled files not committed?

Generated build folders and executables make the repository large and harder to review. Media Fetch AIA keeps source code in Git and distributes compiled builds through GitHub Releases.

## Why does Instagram sometimes need cookies?

Some Instagram media is only available to logged-in users or is restricted by platform-side checks. yt-dlp and gallery-dl may need browser cookies to access those URLs.

## Does the app include ffmpeg?

No. For best results, install ffmpeg separately and make sure it is available on PATH.

## Where are downloads saved?

By default:

```text
%USERPROFILE%\Downloads\Media Fetch AIA
```

You can choose another folder inside the app.

## Which Python version should I use?

Python 3.12 is the recommended version for source runs and local builds.
