# 컴투 TO 컴원 HANDOFF LOG

이 문서는 `컴투 -> 컴원` 현재 outbound 메모 1장만 유지합니다.

## LARGE DIRECTION LABEL

- `컴투 -> 컴원`
- 컴투가 쓰는 문서
- 컴원이 읽는 문서

## READ POSITION

- 여기부터 먼저 읽지 않습니다
- 먼저 `절대규칙.md`
- 그 다음 `PROJECT_READ_FIRST.md`
- 그 다음 `컴투_READ_FIRST.md`
- 그 다음 필요한 경우에만 이 문서를 읽습니다

## TOP SUMMARY

- 현재 상태:
  - downloader 문서 세트 최신화 단계
- 현재 기준:
  - `Video Downloader`
  - source run + one-dir build/release line
  - 최신 source/build 기준 커밋은 `540574a`

## CURRENT ACTIVE NOTE

- date/time:
  - `2026-04-30 KST`
- kept result:
  - `PROJECT_READ_FIRST.md` 최신 기준을 `540574a` 로 맞춤
  - `README.md` 에 Instagram 쿠키/로그인 실패 진단 내용을 보강
  - `컴원_TO_컴투_HANDOFF_LOG.md` 를 최신 인수인계 요약으로 갱신
  - `backup/260430/backup_note_260430.txt` 에 오늘 확인 내용을 남김
- exact first next step:
  - 다음 코드 변경이 있으면 소스 변경, build/dist 영향, 문서 write-back 여부를 같은 턴에 다시 확인
- worktree state:
  - 문서 최신화 완료, 커밋/업로드 시 `git status --short --branch` 로 재확인
