# PROJECT READ FIRST

이 문서가 현재 기준 진실입니다.

부트 문서는 `절대규칙.md` 입니다.

## CURRENT PROJECT TYPE

- 현재 프로젝트: `new_youtube_downloader_gpt`
- 성격: Windows용 `customtkinter` + `yt-dlp` 기반 영상 다운로더
- 앱 이름: `Video Downloader`
- 핵심 소스:
  - `main.py`
  - `gui.py`
  - `downloader.py`
- 빌드 관련:
  - `main.spec`
  - `build_versioned.ps1`
  - `dist/`
  - `build/`

## FIRST READ ORDER

1. `절대규칙.md`
2. `PROJECT_READ_FIRST.md`
3. `컴투`가 메시지 확인이면 `컴투_READ_FIRST.md`
4. `README.md`
5. `BUILD_AND_RELEASE.md`
6. 오늘 날짜 `backup_note_<date>.txt` 가 있으면 그것

이 프로젝트는 실행/배포 문서가 중요하므로, 코드보다 먼저 `README.md` 와 `BUILD_AND_RELEASE.md` 를 읽습니다.

## DAILY START ROUTINE

하루 시작 루틴은 아래 순서로 고정합니다.

1. `다운로드`
2. `메시지 확인`
3. `백업생성`
4. `데일리 업무 리스트 작성 여부 결정`

이 순서를 먼저 끝낸 뒤 본작업으로 들어갑니다.

## CURRENT MILESTONE VERSION

- 공식 기준선: `Video Downloader Windows one-dir release line`
- 의미: 소스 실행과 one-dir 릴리즈 배포 흐름이 함께 정리된 상태
- 해석: 이 프로젝트는 UI 코드뿐 아니라 `빌드/릴리즈 경로`까지 같이 맞아야 기준선으로 봅니다

## CURRENT CODE LINE

- latest source/build baseline commit:
  - `540574a`
  - `Improve Instagram cookie diagnostics`
- current runtime state:
  - Windows용 영상 다운로더로 동작합니다
  - URL 기반 비디오/오디오 다운로드를 지원합니다
  - 해상도, 자막, 중복 파일 처리 정책, 대기열, 히스토리 UI가 있습니다
  - 중복 파일 처리 정책은 `묻기 / 자동 이름 변경 / 덮어쓰기 / 건너뛰기` 를 지원합니다
  - Threads URL은 내부 GraphQL 미디어 정보로 보완해 다운로드합니다
  - Instagram URL은 `yt-dlp` 우선, `gallery-dl` fallback, 브라우저 쿠키 진단 메시지를 함께 사용합니다
  - Instagram 파일명은 `Video by 계정명` 같은 중복 제목 대신 shortcode/id를 포함해 저장합니다
  - Naver Blog URL은 본문에서 `vid/inkey`를 찾아 실제 영상 다운로드를 시도합니다
  - 배포 실행 파일 기준선은 `dist\\releases\\VideoDownloader_codex.exe` + `_internal` 폴더입니다
  - 소스 실행 기준선은 `python main.py` 입니다
- current build state:
  - `VERSION` 현재 값은 `14` 입니다
  - `build_versioned.ps1` 가 버전 관리 + PyInstaller 빌드 + 릴리즈 복사를 담당합니다
  - `main.spec` 는 PyInstaller 기준 파일입니다
  - `main.spec` 는 `VERSION`, 앱 아이콘/PNG, `gallery_dl` data/submodule 을 번들에 포함합니다
  - `build/` 와 `dist/` 는 소스와 구분해서 다룹니다

## TOP SUMMARY

- front-door 문서는 `README.md` 와 `BUILD_AND_RELEASE.md` 입니다
- 소스 기준선은 `main.py`, `gui.py`, `downloader.py` 입니다
- 배포 기준선은 one-dir 구조입니다
- 실행 파일만 따로 옮기면 안 되고 `_internal` 과 같은 위치에 있어야 합니다
- 2026-04-30 문서 갱신 시작 시점의 `main` 과 `origin/main` 은 `540574a` 로 맞아 있었습니다

## CURRENT STABLE BASELINE

- repo baseline:
  - source/build commit `540574a`
  - README / build guide / handoff 문서 세트가 있으며, Threads 지원과 Instagram 쿠키 진단 개선까지 반영된 상태입니다
- runtime baseline:
  - Python 3.12 기준 소스 실행
  - PyInstaller one-dir 릴리즈 기준

## OPTIONAL FOLLOW-UP WORK

1. `build/` 와 `dist/` 를 어느 범위까지 Git에 남길지 기준 정리
2. 실행 확인 절차를 `BUILD_AND_RELEASE.md` 와 더 밀착시키기
3. Instagram / Threads / Naver Blog 별 수동 smoke test 결과를 release note 에 남기기
4. 변경이 생기면 backup note 와 build 영향도를 같은 턴에 정리

## EXACT COMMAND WORDS

### `메시지 확인`

- 이 문서를 먼저 읽습니다
- `컴투`면 `컴투_READ_FIRST.md` 와 `컴원_TO_컴투_HANDOFF_LOG.md` 를 먼저 읽습니다
- 그 다음 `README.md`, `BUILD_AND_RELEASE.md` 를 읽습니다
- 답변에는 아래 5개가 들어갑니다
- 현재 앱 성격
- 이미 끝난 것
- 남아 있는 빌드/배포 리스크
- 다음 첫 액션
- 현재 worktree 상태

### `업로드 명령`

- local `HEAD`
- `origin/main`
- worktree 변경 범위
- build/dist 포함 여부
- backup note 작성 여부

위 5개를 먼저 확인한 뒤 push 여부를 판단합니다.
