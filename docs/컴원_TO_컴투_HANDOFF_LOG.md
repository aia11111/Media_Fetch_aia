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
- 현재 pushed main:
  - `d3902eb`
- 현재 local 상태:
  - `PROJECT_READ_FIRST.md` 를 추가해 front-door 문서 세트를 만들었습니다
  - `README.md` 와 `BUILD_AND_RELEASE.md` 를 먼저 읽는 기준을 고정했습니다
  - 문서 closeout 기준으로 `컴원_TO_컴투_HANDOFF_LOG.md` 를 추가했습니다

## CURRENT ACTIVE OUTBOUND NOTE

- date/time:
  - `2026-04-14 KST`
- user intent:
  - 프로젝트별 문서 세트를 refactor 형식에 맞춰 정리하되, 판타지는 제외하고 진행
- kept result:
  - `docs/PROJECT_READ_FIRST.md` 추가
  - 앱 성격, 실행 기준, build/dist 구분, 업로드 확인 규칙 정리
  - 이번 문서 closeout 기준으로 `컴원_TO_컴투_HANDOFF_LOG.md` 추가
- risk or ambiguity:
  - 이 프로젝트는 빌드 산출물이 커지기 쉬워서, 실제 업로드 전에는 `build/`, `dist/` 포함 여부를 다시 확인해야 합니다
  - 현재는 문서 bootstrap 단계라 inbound handoff 세트까지는 아직 없습니다
- exact first next step:
  - 다음 변경이 빌드/배포 관련이면 `README.md`, `BUILD_AND_RELEASE.md`, backup note, handoff 를 같은 턴에 같이 갱신
- worktree state:
  - 문서 추가 상태, 아직 이번 턴 커밋/업로드 전
