# Search Feature Implementation Plan (2026-04-28)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 자막·메모·영상을 키워드로 빠르게 찾고 해당 시점으로 점프할 수 있게 한다 (전역 ⌘K 모달 + 헤더 검색바, 영상 내 ⌘F 오버레이).

**Architecture:** SQLite LIKE 풀스캔 기반 검색 서비스 추가 (백엔드 무스키마 변경) + 프론트엔드에 검색 UI 컴포넌트 4종 (헤더 SearchBar, 글로벌 SearchModal, 영상 내 InVideoSearchOverlay, 결과 카드). 결과 클릭 → 기존 `openMemo` 흐름 재사용.

**Tech Stack:** Python 3.11 · FastAPI · SQLModel · pytest · uv · SvelteKit · TypeScript · Tailwind · Vitest

**Spec:** `docs/superpowers/specs/2026-04-28-search-design.md`

**커밋 규약**: 본 플랜의 모든 커밋 메시지에 AI 관련 흔적 (`Co-Authored-By: Claude...`, "Generated with..." 등) **금지**. 메시지는 일반 개발자 톤. 로컬 git config의 user.name=`svrforum.com`, user.email=`svrforum.com@gmail.com` 그대로 사용.

---

## Phase 목차

- [Phase 1 — Backend: search 서비스 + API + 테스트](phase-01-backend-search.md)
- [Phase 2 — Frontend: 타입 + API 클라이언트 + 스토어](phase-02-frontend-foundation.md)
- [Phase 3 — Frontend: 헤더 SearchBar + 글로벌 SearchModal + ⌘K](phase-03-global-search-ui.md)
- [Phase 4 — Frontend: 영상 내 ⌘F 오버레이 + 매치 하이라이트](phase-04-in-video-search.md)
- [Phase 5 — 통합 검증 + 문서 + 머지](phase-05-verify-merge.md)

## 실행 순서

Phase 1 → 2 → 3 → 4 → 5 순차. 의존성:
- 2는 1의 API 응답 포맷 사용
- 3은 2의 스토어/클라이언트 사용
- 4는 3과 독립 (영상 내 검색은 클라이언트 사이드 only)

## 완료 기준

- [ ] 백엔드 `GET /api/search?q=` 동작 (자막+메모+영상 제목 매치)
- [ ] 헤더 검색바 항상 visible, 클릭 → 모달
- [ ] ⌘K / Ctrl+K → 어디서든 모달 오픈
- [ ] 결과 클릭 → 해당 영상으로 이동 + 해당 시점 seek
- [ ] ReadyScreen 내 ⌘F → 오버레이 노출, 매치 강조, Enter/↑↓ 점프
- [ ] Esc로 모든 검색 UI 닫기
- [ ] `uv run pytest` 142 → 151+ 모두 pass
- [ ] `npm run check` 0 errors, `npm test` 그대로 4 pass
- [ ] docker compose 재빌드 후 동작 확인 (Playwright smoke)
- [ ] `docs/architecture.md` 기능 카탈로그에 검색 추가
- [ ] `feature/search` → master 머지 + push

## 브랜치 전략

- 시작 시 `master`에서 `feature/search` 생성
- 모든 커밋은 `feature/search`에
- Phase 5에서 `--no-ff` 머지로 master에 통합 + GitHub push
