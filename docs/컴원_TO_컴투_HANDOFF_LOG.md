# 컴원 TO 컴투 HANDOFF LOG

이 문서는 `컴원 -> 컴투` 현재 outbound 메모 1장만 유지합니다.

## LARGE DIRECTION LABEL

- `컴원 -> 컴투`
- 컴원이 쓰는 문서
- 컴투가 읽는 문서

## READ POSITION

- 여기부터 먼저 읽지 않습니다
- 먼저 `절대규칙.md`
- 그 다음 `PROJECT_READ_FIRST.md`
- 그 다음 `README.md`
- 그 다음 `BUILD_AND_RELEASE.md`
- 그 다음 필요한 경우에만 이 문서를 읽습니다

## TOP SUMMARY

- 현재 핵심 기준:
  - `Video Downloader`
  - `customtkinter + yt-dlp` 기반 Windows용 다운로더
  - 소스 실행과 one-dir 릴리즈 배포를 함께 보는 구조
- 최신 source/build 기준:
  - `540574a`
- 현재 local 상태:
  - 2026-04-30 문서 갱신 시작 시점에는 `main` 과 `origin/main` 이 같은 커밋이었습니다
  - `PROJECT_READ_FIRST.md`, `README.md`, `BUILD_AND_RELEASE.md`, 컴투 read-first/handoff 문서가 있습니다
  - 최신 기능 기준은 Threads 지원, Instagram 쿠키 진단 개선, Naver Blog 보완 다운로드입니다

## CURRENT ACTIVE OUTBOUND NOTE

- date/time:
  - `2026-04-30 KST`
- user intent:
  - 업로드/인수인계 전에 컴투가 현재 상태를 바로 이해할 수 있는지 문서 상태 확인
- kept result:
  - `PROJECT_READ_FIRST.md` 의 기준 커밋을 `540574a` 로 최신화
  - Instagram 쿠키 진단 개선, Threads 지원, Naver Blog 처리 기준을 문서 요약에 반영
  - `README.md` 에 Instagram 실패 진단 동작을 추가 설명
  - 오늘 날짜 backup note 를 남김
- risk or ambiguity:
  - 이 프로젝트는 빌드 산출물이 커지기 쉬워서, 실제 업로드 전에는 `build/`, `dist/` 포함 여부를 다시 확인해야 합니다
  - 현재 build/dist 산출물은 repo 에 포함된 상태이며, 산출물만 직접 수정하지 않는 기준을 유지합니다
- exact first next step:
  - 실제 배포 전에는 `python -m py_compile gui.py downloader.py main.py` 를 먼저 돌리고, 필요 시 `build_versioned.ps1 -NoBump` 로 릴리즈 폴더를 재확인
- worktree state:
  - 문서 최신화 완료, 커밋/업로드 시 `git status --short --branch` 로 재확인
