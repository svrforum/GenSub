# CLAUDE.md

GenSub 프로젝트에서 Claude Code 세션 및 개발자 공통으로 따르는 규약.

## 프로젝트 요약

**GenSub** — YouTube URL이나 로컬 영상 파일을 받아 Whisper로 자막을 생성하고, 브라우저에서 편집·시청·다운로드할 수 있는 자체 호스팅 웹 서비스. `docker compose up` 한 번으로 구동.

스택: Python 3.11 · FastAPI · SQLModel(SQLite WAL) · faster-whisper · yt-dlp · ffmpeg · uv · SvelteKit(adapter-static, SPA) · Tailwind · Docker Compose.

단일 이미지를 `GENSUB_ROLE=api|worker`로 분기. 자세한 아키텍처는 [`docs/architecture.md`](docs/architecture.md).

---

## 1. 코드 컨벤션

### Python (backend/)

- 버전: Python 3.11+.
- 타입 힌트 필수 (테스트 파일 제외). `from __future__ import annotations`는 쓰지 않음 (3.11 PEP 604 문법 사용).
- Lint: `ruff` 규칙 `E, F, I, N, UP, B, SIM`. 라인 100자.
- Format: ruff가 포매터 역할도 함. `ruff check --fix .`.
- async: FastAPI 라우터는 `async def` 우선. DB 작업은 SQLAlchemy 동기 세션이므로 `async def` 안에서 blocking 호출도 허용 (SQLite는 단일 프로세스라 이득 없음).
- import 순서: stdlib → 3rd party → local. ruff I 규칙이 강제함.

### TypeScript / Svelte (frontend/)

- `tsconfig.strict = true`.
- `<script lang="ts">` 기본. JS 파일은 만들지 않음.
- 컴포넌트 파일 **300줄 초과 시 분리 검토**. 책임이 하나가 아니라는 신호.
- Tailwind 우선. 별도 CSS 파일은 최소화.
- 스토어는 `frontend/src/lib/stores/`에만. 컴포넌트에서 직접 `localStorage` 접근 금지 — 스토어를 경유.

---

## 2. 아키텍처 규칙 (위반 시 레이어 경계 파괴)

### 백엔드 레이어

```
api/ (라우터)  →  services/ (도메인)  →  models/ (엔티티)
                         ↓
                      core/ (설정·DB)
```

- **`api/` 라우터 안에서 `Session(engine)`을 직접 열지 않는다.** 상태 변경은 `services/` 함수를 호출해서 위임.
- **Job 상태 전이는 반드시 `services/job_state.py` 경유.** 다른 곳에서 `job.status =` 직접 쓰지 않음.
- 파이프라인 단계 추가/수정은 `services/pipeline.py`에만. 워커 폴링 루프(`worker/main.py`)는 건드리지 않는다.
- 설정은 `app/core/settings.py`의 `Settings` 클래스에만 추가. 코드 어디서도 `os.environ[...]` 직접 접근 금지.

### 프론트엔드 구조

- `screens/` ← 상태별 최상위 화면. `current` 스토어의 `screen` 필드로 분기.
- `ui/` ← 재사용 컴포넌트. 상태 스토어 import 최소화, props로 받는 것을 우선.
- `api/` ← fetch 래핑. 컴포넌트에서 `fetch()` 직접 호출 금지.

---

## 3. 테스트 규칙

- 위치: `backend/tests/test_<module_or_feature>.py`.
- 프레임워크: pytest + `pytest-asyncio` (`asyncio_mode = auto`).
- **새 서비스·엔드포인트 추가 시 테스트 동반 필수.**
- **리팩토링 시작 전 반드시 `uv run pytest` 그린 확인** — 기준선 없이 변경 금지.
- 테스트는 하나의 동작을 검증. 여러 assert가 들어가는 건 허용하되 다른 기능을 한 테스트에서 검증하지 않음.
- 통합 테스트는 `TestClient` 또는 `httpx.AsyncClient` 사용. 실제 SQLite 파일(`tmp_path` fixture) 권장, 인메모리 DB는 테이블 공유 이슈로 피함.

---

## 4. 커밋 / 브랜치 규칙

### 컨벤셔널 커밋

타입 prefix: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `style`, `perf`.

예: `fix(frontend): sidebar ttl now reads from /api/config`.

### 메시지는 **왜** 중심

"무엇이 바뀌었는지"가 아니라 "왜 바꿨는지"를 먼저. 무엇은 diff가 말해준다.

### 브랜치

- `master`: 주 브랜치.
- `feature/*`: 새 기능.
- `refactor/*`: 리팩토링.
- `fix/*`: 버그 수정.

병합은 기본 `--no-ff` (히스토리 보존). Squash는 정말 작은 변경일 때만.

---

## 5. Claude Code / 에이전트 동작 규약

### 5.1 모델 고정: Opus 4.7

이 프로젝트의 **모든 Claude Code 세션과 dispatch하는 Agent는 `claude-opus-4-7` 사용**.

- 직접 실행: 세션 진입 시 모델이 Opus 4.7인지 확인.
- `Agent` tool 호출 시 **반드시** `model: "opus"` 인자 명시. 기본값 의존 금지.
- Haiku/Sonnet로의 다운그레이드 제안 금지.

### 5.2 리팩토링 전 기준선

어떤 리팩토링 작업이든 시작 전에 `cd backend && uv run pytest`로 그린 확인. 이미 실패하고 있는 테스트를 내 변경이 유발한 것처럼 착각하는 걸 방지.

### 5.3 경로 규칙

- 도구에 전달하는 파일 경로는 항상 **절대경로**.
- Bash 명령에서도 `cd /Users/loki/GenSub` 기준으로 작업.

### 5.4 worktree 사용

긴 리팩토링이나 충돌 가능성 있는 실험은 `superpowers:using-git-worktrees` 스킬 사용. 단, `.worktrees/`는 `.gitignore`에 포함돼 있으므로 그 안에 저장소 파일을 추가해도 추적되지 않음 — 작업 완료 후 브랜치 머지를 통해서만 변경이 master로 들어간다.

### 5.5 문서 경로 규칙

| 파일 | 역할 |
|---|---|
| `docs/architecture.md` | **현재 상태**. 코드와 동기화. 구조 변경 시 같은 PR에서 업데이트. |
| `docs/superpowers/specs/YYYY-MM-DD-*.md` | **변경 제안** (시간 스냅샷). 승인 후 보존, 수정하지 않음. |
| `docs/superpowers/plans/*/` | 실행 플랜 (체크리스트). 진행 중 체크 표시. 완료 후 보존. |
| `CLAUDE.md` | 본 규약. 모든 개발이 따른다. |
| `README.md` | 외부 독자용 소개. |

### 5.6 스펙 vs 현재 상태 충돌 시

구 설계 스펙(`2026-04-11-gensub-design.md`)과 현재 구현이 다른 경우:
- 판단 기준은 **`docs/architecture.md` + 실제 코드**.
- 구 스펙은 설계 의도 참고용이지 현재 상태의 정답이 아님.

### 5.7 위반 요청 처리

사용자 요청이 본 파일과 충돌할 때 (예: "Sonnet으로 빠르게 해줘"):
- 먼저 충돌 사실을 알림.
- 요청이 지속되면 `CLAUDE.md` 업데이트를 제안 (규약을 바꾸든가, 예외 사유를 기록하든가).
- 기억(memory)에만 남기는 건 금지 — 규약은 파일로.

---

## 6. 흔한 작업 체크리스트

### 새 엔드포인트 추가

1. `services/`에 순수 함수 작성 + 단위 테스트.
2. `api/`에 라우터 추가 — `services` 함수 호출만 수행.
3. 통합 테스트 (`TestClient`) 추가.
4. `frontend/src/lib/api/`에 클라이언트 함수 추가.
5. 필요 시 `docs/architecture.md`의 엔드포인트 표 업데이트.

### 새 자막 포맷 추가

1. `services/subtitles.py`에 `format_xxx()` 함수.
2. `api/media.py`에 다운로드 엔드포인트.
3. 프론트 `DownloadBar.svelte`에 버튼.
4. 테스트 추가.

### Job 상태 전이 추가

1. `models/job.py`의 `JobStatus` enum에 값 추가.
2. `services/job_state.py`에 전이 함수 추가 (`mark_xxx()`).
3. `services/pipeline.py`에서 전이 지점 배치.
4. 프론트 `current.ts`의 `screen` 매핑 확장.
5. `docs/architecture.md`의 상태 다이어그램 업데이트.
