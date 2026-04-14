# Build And Release

## 목적

이 문서는 로컬에서 `Video Downloader`를 빌드하고 릴리즈 폴더를 갱신하는 절차를 정리합니다.

## 전제

- Windows 환경
- Python 3.12 설치
- `requirements.txt` 의존성 설치 완료

## 1. 문법 확인

```powershell
python -m py_compile gui.py downloader.py main.py
```

## 2. 빌드

```powershell
powershell -ExecutionPolicy Bypass -File .\build_versioned.ps1
```

버전 유지 빌드:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_versioned.ps1 -NoBump
```

## 3. 결과물 확인

최종 실행 파일:

`dist\\releases\\VideoDownloader_codex.exe`

필수 런타임 폴더:

`dist\\releases\\_internal`

중간 빌드 결과:

- `dist\\main\\main.exe`
- `dist\\main\\VideoDownloader_codex.exe`

## 4. 배포 시 주의

- one-dir 방식이라 exe만 따로 전달하면 실행되지 않습니다.
- 반드시 `_internal`과 함께 전달해야 합니다.
- 실행 중인 상태에서는 릴리즈 exe 또는 `_internal` 덮어쓰기가 실패할 수 있습니다.

## 5. 버전 규칙

- `VERSION` 파일은 두 자리 숫자 형식
- 빌드 스크립트는 기본적으로 버전을 1 증가시킴
- `-NoBump` 사용 시 버전 유지

