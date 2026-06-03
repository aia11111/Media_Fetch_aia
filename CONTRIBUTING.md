# Contributing

Thanks for helping improve Media Fetch AIA. Please keep contributions focused, legal, and easy to review.

## Bug Reports

When reporting a bug, include:

- Windows version
- Python version, if running from source
- App version or commit hash
- Platform or URL type involved, such as YouTube, Instagram, Threads, or Naver Blog
- Steps to reproduce
- Expected result and actual result
- Relevant error messages, with tokens, cookies, private URLs, and account data removed

## Feature Requests

Feature requests should explain:

- The workflow or problem you want to improve
- Why the feature matters
- Any platform-specific constraints
- Whether the feature can be implemented without bypassing access controls

## Local Development

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the app:

```powershell
python main.py
```

Check syntax before opening a pull request:

```powershell
python -m py_compile gui.py downloader.py main.py
```

## Pull Requests

- Keep PRs small and clearly scoped.
- Do not include unrelated refactoring.
- Do not commit generated build output, caches, logs, downloads, or local backup files.
- Update documentation when behavior, build steps, or user-facing workflows change.
- Explain what changed and how it was checked.

## Legal Use

Contributions must preserve lawful use boundaries. Do not add features intended to bypass DRM, paywalls, login restrictions, authentication, or platform access controls.

Media Fetch AIA is intended only for media that the user owns, has permission to download, or is legally allowed to archive.
