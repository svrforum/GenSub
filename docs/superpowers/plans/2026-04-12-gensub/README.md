# GenSub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** YouTube URL이나 로컬 영상 파일을 받아 Whisper로 자막을 생성하고, 브라우저에서 편집·시청·다운로드할 수 있는 자체 호스팅 웹 서비스를 `docker compose up` 한 번으로 동작하도록 구현한다.

**Architecture:** FastAPI API + 별도 Python 워커(동일 이미지, `GENSUB_ROLE`로 분기) + SQLite 작업 큐(WAL) + 공유 bind mount 볼륨. 프론트엔드는 SvelteKit을 adapter-static으로 빌드해 백엔드가 정적 파일로 서빙. 진행률은 SSE로 스트리밍, 영상은 HTTP Range로 브라우저에 전달.

**Tech Stack:** Python 3.11 / FastAPI / SQLModel / uv / faster-whisper / yt-dlp / ffmpeg / mkvtoolnix · SvelteKit / Tailwind CSS / Pretendard Variable / lucide-svelte / svelte/motion · Docker Compose

**Spec:** `docs/superpowers/specs/2026-04-11-gensub-design.md`

---

## 페이즈 목차

- [Phase 0 — Project Scaffolding](phase-00.md)
- [Phase 1 — Backend Foundation (설정, DB, 모델)](phase-01.md)
- [Phase 2 — Job Management API](phase-02.md)
- [Phase 3 — Pipeline Services (파이프라인 순수 함수들)](phase-03.md)
- [Phase 4 — Worker Process (파이프라인 오케스트레이션)](phase-04.md)
- [Phase 5 — Media Serving Endpoints](phase-05.md)
- [Phase 6 — Segment Editing Endpoints](phase-06.md)
- [Phase 7 — Backend Docker Smoke Test](phase-07.md)
- [Phase 8 — Frontend Scaffolding + Design Tokens](phase-08.md)
- [Phase 9 — Frontend API Client + Stores](phase-09.md)
- [Phase 10 — Idle Screen (Step 1)](phase-10.md)
- [Phase 11 — Processing Screen (Step 2)](phase-11.md)
- [Phase 12 — Ready Screen (Step 3) — Player + Editor](phase-12.md)
- [Phase 13 — Burn-in Bottom Sheet (Step 4)](phase-13.md)
- [Phase 14 — Header + Recent Jobs + Error Polish](phase-14.md)
- [Phase 15 — Full Stack Integration & E2E](phase-15.md)

## 실행 순서

위 페이즈를 순서대로 처리하세요. 각 페이즈 파일은 Task N.M 단위의 체크박스 스텝으로 구성되어 있으며, 독립적으로 실행·리뷰할 수 있도록 설계되었습니다.

- **페이즈 0~7**: 백엔드 (FastAPI + 워커 + SQLite)
- **페이즈 8~14**: 프론트엔드 (SvelteKit SPA)
- **페이즈 15**: 풀 스택 통합 및 E2E 검증

Phase 7 완료 시점에 백엔드 단독으로 curl 기반 사용이 가능하고, Phase 15 완료 시점에 `docker compose up`만으로 전체 서비스가 동작합니다.
