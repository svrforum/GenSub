# Memo Feature Implementation Plan (2026-04-22)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 자막 세그먼트 단위 북마크 + 선택적 메모를 저장하고, 영상과 무관한 전역 메모 리스트에서 조회·"보러가기"할 수 있게 한다.

**Architecture:** 백엔드는 새 `memo` 테이블 + 서비스 + API 라우터 추가 (기존 스키마 무변경). 프론트는 사이드바 2탭(영상/메모), SegmentList 내 📎 버튼, 글로벌 MemoCard 리스트, `current.initialTime`을 통한 자동 seek. 메모 있는 Job은 자동 pin되어 TTL로 안 만료.

**Tech Stack:** Python 3.11 · FastAPI · SQLModel(SQLite WAL) · pytest · uv · SvelteKit · TypeScript · Tailwind · Docker

**Spec:** `docs/superpowers/specs/2026-04-22-memo-feature-design.md`

**모델 규약**: 

---

## Phase 목차

- [Phase 1 — Backend: Memo 모델 + 서비스](phase-01-backend-model-service.md)
- [Phase 2 — Backend: API 엔드포인트 + Job 삭제 cascade](phase-02-backend-api.md)
- [Phase 3 — Frontend: 타입 + API + 스토어 + current.initialTime](phase-03-frontend-foundation.md)
- [Phase 4 — Frontend: SegmentMemo (저장 버튼 + 인라인 메모)](phase-04-frontend-segment-memo.md)
- [Phase 5 — Frontend: 사이드바 탭 + MemoCard + 보러가기 seek](phase-05-frontend-sidebar-navigate.md)
- [Phase 6 — 통합 검증 + 문서 + 머지](phase-06-verify-merge.md)

## 실행 순서

Phase 1 → 2 → 3 → 4 → 5 → 6 순차. Phase 간 의존성:
- 2는 1의 서비스 함수 사용
- 3은 1·2의 API 계약 필요
- 4·5는 3의 타입/스토어 필요
- 5는 4와 독립 (사이드바는 segment list와 별도)

## 완료 기준

- [ ] 새 `memo` 테이블 자동 생성, 기존 `job`/`segment` 데이터 무영향
- [ ] 세그먼트 📎 1클릭 저장 / 재클릭 해제 (메모 내용 있으면 409 → 확인 다이얼로그)
- [ ] 전역 메모 리스트 (사이드바 메모 탭) 최신순 표시, `job_alive` 반영
- [ ] 메모 클릭 → 해당 영상 이동 + 해당 시점 자동 seek
- [ ] 메모 있는 Job 자동 pin, Job 삭제 시 확인 다이얼로그에 "메모 N개도 함께" 경고
- [ ] `uv run pytest` 기존 95 + 신규 memo 테스트 전부 pass
- [ ] 프론트 `npm run check` 0 errors, `npm run build` 성공
- [ ] docker 재빌드 + 기동 후 기존 job `059ddd86…` 접근 OK
- [ ] `docs/architecture.md` 기능 카탈로그에 메모 항목 추가
- [ ] `feature/memo` 브랜치가 master로 머지

## 브랜치 전략

- 시작 시 `master` 에서 `feature/memo` 브랜치 생성
- 모든 커밋은 `feature/memo` 에
- Phase 6 완료 시점에 `--no-ff` 머지로 master 통합
