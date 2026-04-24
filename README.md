# Video Downloader

`customtkinter` + `yt-dlp` 기반의 Windows용 영상 다운로더입니다.

현재 앱 이름은 `Video Downloader`이며, 실행 파일은 one-dir 방식으로 배포됩니다.

## 주요 기능

- YouTube, Instagram, Threads, Naver Blog 등 URL 기반 영상 다운로드
- 비디오 / 오디오 다운로드 선택
- 해상도 선택 및 자막 다운로드 옵션
- 중복 파일 감지 및 `묻기 / 덮어쓰기 / 건너뛰기` 정책
- 대기열 기반 연속 다운로드
- 썸네일, 히스토리, 파일 열기 UI 제공
- Windows URL 프로토콜 `yg-download://` 등록 지원

## 현재 실행 파일

최신 릴리즈 실행 경로:

`dist\\releases\\VideoDownloader_codex.exe`

필수 의존 폴더:

`dist\\releases\\_internal`

주의:

- exe만 단독으로 옮기면 실행되지 않습니다.
- `_internal` 폴더와 같은 위치에 두고 실행해야 합니다.

## 소스 실행

권장 Python:

- `Python 3.12`

의존성 설치:

```powershell
python -m pip install -r requirements.txt
```

앱 실행:

```powershell
python main.py
```

## 빌드

문법 확인:

```powershell
python -m py_compile gui.py downloader.py main.py
```

빌드 + 릴리즈 복사:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_versioned.ps1
```

버전 올리지 않고 현재 버전으로 다시 빌드:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_versioned.ps1 -NoBump
```

빌드 스크립트 동작:

- `VERSION` 값을 읽고 필요 시 증가
- `main.spec`로 `PyInstaller` 빌드 실행
- `dist\\main\\main.exe`를 `dist\\releases\\VideoDownloader_codex.exe`로 복사
- `dist\\main\\_internal`을 `dist\\releases\\_internal`로 복사

## 설정 / 기록 위치

앱 설정 폴더:

`%USERPROFILE%\\.new_youtube_downloader`

주요 파일:

- `settings.json`
- `download_history.json`

기본 다운로드 폴더:

`%USERPROFILE%\\Downloads\\Video Downloader`

## 현재 버전 체계

- `VERSION` 파일은 두 자리 숫자 형식 사용
- 예: `12` -> 앱 내부에는 `v12`로 표시

## 참고 사항

- 인스타그램 다운로드는 공개 URL 기준으로 `yt-dlp` 우선, 필요 시 `gallery-dl` fallback 경로를 사용합니다.
- Threads 다운로드는 `yt-dlp`가 직접 지원하지 않는 URL을 내부 GraphQL 미디어 정보로 보완해 처리합니다.
- Naver Blog 영상은 블로그 본문에서 `vid/inkey`를 추출해 실제 영상 다운로드를 시도합니다.
- Windows 시작 단계에서 Per-monitor DPI v2를 우선 적용하고, 실패 시 구버전 DPI 설정으로 fallback합니다.
- Tkinter 글자 스케일은 현재 창이 위치한 모니터 DPI에 맞춰 보정합니다.

## 저장소 구성

- `gui.py`: UI
- `downloader.py`: 다운로드 로직
- `main.py`: 앱 진입점 및 URL 프로토콜 등록
- `main.spec`: PyInstaller 설정
- `build_versioned.ps1`: 빌드 및 릴리즈 스크립트
