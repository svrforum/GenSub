# Stability Refactor + Docs 실행 플랜 (2026-04-18)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GenSub의 현재 구현을 master 브랜치로 정상화하고, 레이어 경계·취소 경로·설정 단절 이슈 7건(R1~R7)을 수정하며, `docs/architecture.md`·`CLAUDE.md`·`README.md` 3종 문서 축을 세운다.

**Architecture:** 5단계 실행:
1. Git 정리 (feature/gensub → master 머지 후 refactor/stability 브랜치)
2. 문서 3종 작성 + 스크린샷 정리
3. R1~R7 리팩토링 (작은 것부터, 커밋 단위로 분리)
4. 통합 검증 (pytest + docker compose + 수동 smoke)
5. 머지 + 구 스펙 안내 추가

**Tech Stack:** Git · Python 3.11 · FastAPI · SQLModel · pytest · uv · SvelteKit · TypeScript · Tailwind · Docker Compose

**Spec:** `docs/superpowers/specs/2026-04-18-stability-refactor-design.md`

**모델 규약**: 본 플랜을 실행하는 모든 에이전트·서브태스크는 **Opus 4.7** 사용. `Agent` tool 호출 시 `model: "opus"` 명시.

---

## Phase 목차

- [Phase 1 — Git 정리 (머지 + 브랜치)](phase-01-git.md)
- [Phase 2 — 문서 3종 + 스크린샷 정리](phase-02-docs.md)
- [Phase 3 — R1~R7 리팩토링](phase-03-refactor.md)
- [Phase 4 — 통합 검증](phase-04-verify.md)
- [Phase 5 — 머지 + 완료 처리](phase-05-complete.md)

## 실행 순서

Phase 1 → 2 → 3 → 4 → 5 순차 실행. Phase 2 내의 세 문서 파일은 서로 독립이라 병렬 가능.

Phase 3의 R1~R7은 **작은 것부터 큰 순서**로 배치돼 있고, 각 R은 독립 커밋이라 중간에 멈춰도 상태가 안전함.

## 완료 기준

- [ ] 루트에서 `git log --oneline | wc -l` ≥ 114
- [ ] `.worktrees/` 제거됨
- [ ] `docs/architecture.md`, `CLAUDE.md`, 새 `README.md` 3파일 존재
- [ ] 루트 `gensub-*.png` 2장만 `docs/images/`에 남고 나머지 삭제
- [ ] `cd backend && uv run pytest` 전부 그린 (예상 38개)
- [ ] `docker compose build` 성공
- [ ] `refactor/stability`가 master로 머지됨
- [ ] 구 스펙(`2026-04-11-gensub-design.md`) 상단에 "현재 상태는 architecture.md" 안내 헤더 존재
