# Build And Release

This guide documents the local build flow for Media Fetch AIA.

## Prerequisites

- Windows
- Python 3.12
- Dependencies installed with `python -m pip install -r requirements.txt`
- PyInstaller available in the active Python environment

## Syntax Check

```powershell
python -m py_compile gui.py downloader.py main.py
```

## Build

Build and bump the rolling `VERSION` value:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_versioned.ps1
```

Build without changing `VERSION`:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_versioned.ps1 -NoBump
```

## Output

Primary PyInstaller output:

```text
dist\main\main.exe
```

Release copy:

```text
dist\releases\MediaFetchAIA.exe
```

Runtime dependencies:

```text
dist\releases\_internal
```

## Distribution

Do not commit `build/`, `dist/`, or generated executables to Git.

For public distribution, upload the release executable and its required one-dir `_internal` folder as a GitHub Releases asset. The executable will not run correctly if it is separated from `_internal`.

## Versioning

- `VERSION` uses a two-digit rolling release number.
- Example: `15` is displayed in the app as `v15`.
- The build script increments `VERSION` unless `-NoBump` is provided.
