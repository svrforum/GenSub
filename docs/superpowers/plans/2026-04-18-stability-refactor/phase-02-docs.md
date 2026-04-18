# Phase 2 — 문서 3종 + 스크린샷 정리

목표: `docs/architecture.md`, `CLAUDE.md`, 새 `README.md`를 작성하고 루트의 스크린샷을 정리한다. 4개 Task는 서로 독립이라 순서 자유. 모든 작업은 `refactor/stability` 브랜치에서.

---

### Task 2.1: 스크린샷 정리

**Files:**
- Create: `docs/images/gensub-idle-screen.png` (기존 루트 파일 이동)
- Create: `docs/images/gensub-final-ready.png` (기존 루트 파일 이동)
- Delete: 루트의 39개 `gensub-*.png`
- Modify: `.gitignore`

- [ ] **Step 1: 브랜치 확인**

```bash
cd /Users/loki/GenSub
git branch --show-current
```

Expected: `refactor/stability`

- [ ] **Step 2: `docs/images/` 디렉토리 생성 및 2장 이동**

```bash
mkdir -p docs/images
mv gensub-idle-screen.png docs/images/
mv gensub-final-ready.png docs/images/
ls docs/images/
```

Expected: 두 파일 모두 `docs/images/`에 존재.

- [ ] **Step 3: 나머지 `gensub-*.png` 삭제**

```bash
ls gensub-*.png 2>/dev/null | wc -l
rm -f gensub-*.png
ls gensub-*.png 2>/dev/null | wc -l
```

Expected: 첫 명령 39, 마지막 명령 0.

- [ ] **Step 4: `.gitignore`에 `/gensub-*.png` 패턴 추가**

Read current `.gitignore`, append pattern. Current `.gitignore` has one line `.worktrees/`. Replace with:

```bash
cat >> .gitignore <<'EOF'

# 루트에 playwright 스크린샷이 실수로 쌓이는 것 방지
/gensub-*.png
EOF
cat .gitignore
```

Expected: `.worktrees/` + 새 패턴 포함.

- [ ] **Step 5: 커밋**

```bash
git add .gitignore docs/images/
git rm --cached --ignore-unmatch gensub-*.png 2>/dev/null || true
# 삭제된 파일들도 스테이징
git add -A
git status --short
git commit -m "$(cat <<'EOF'
chore: relocate screenshots to docs/images/ and clean root

- Keep 2 canonical screenshots (idle, final-ready) under docs/images/
- Delete 39 Playwright session artifacts from repo root
- Add /gensub-*.png to .gitignore to prevent future accumulation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2.2: `CLAUDE.md` 작성

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: 파일 작성**

Write `CLAUDE.md`:

````markdown
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
````

- [ ] **Step 2: 커밋**

```bash
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: add CLAUDE.md with dev and agent conventions

코드 컨벤션, 아키텍처 레이어 규칙, 테스트/커밋 규약, Claude Code
에이전트 동작 규칙(모델=Opus 4.7 고정 등), 문서 경로 규칙 정리.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2.3: `docs/architecture.md` 작성

**Files:**
- Create: `docs/architecture.md`

이 문서는 현재 구현 상태의 "지도" 역할. Phase 3에서 구조가 약간 바뀌므로(특히 R1: regenerate 제거, R2: services/jobs.py 확장, R6: services/backup.py 신설), **Phase 3 완료 후 최종 반영이 안전**. 하지만 spec §3에서 Phase 2 → Phase 3 순서를 명시했으므로, 여기서 **포스트-리팩토링 상태**를 반영해 미리 기술한다(작은 변경이라 안전).

- [ ] **Step 1: 파일 작성**

Write `docs/architecture.md`:

````markdown
# GenSub Architecture (현재 상태)

이 문서는 **현재 구현된 시스템의 상태**를 기록한다. 설계 의도(왜 이렇게 만들었나)는
[`docs/superpowers/specs/2026-04-11-gensub-design.md`](superpowers/specs/2026-04-11-gensub-design.md)를, 개발 규약은
[`CLAUDE.md`](../CLAUDE.md)를 참고.

구조가 바뀌면 **같은 PR**에서 이 문서도 업데이트한다.

---

## 1. 한눈에 보기

**GenSub**은 YouTube 영상 URL 또는 로컬 업로드 파일을 받아 Whisper로 자막을 생성하고, 브라우저에서 편집·스트리밍·다운로드할 수 있게 해주는 자체 호스팅 웹 서비스다. `docker compose up` 한 번으로 구동.

### 기술 스택

| 레이어 | 기술 |
|---|---|
| API/정적서빙 | FastAPI (`uvicorn --factory`) |
| 워커 | 독립 Python 프로세스, SQLite 폴링 |
| 큐/영속화 | SQLite (WAL, `synchronous=FULL`, `busy_timeout`) |
| STT | faster-whisper (CPU int8 / GPU float16) |
| 비디오/오디오 | yt-dlp, ffmpeg, mkvtoolnix |
| 프론트엔드 | SvelteKit (adapter-static, SPA) |
| UI | Tailwind CSS, Pretendard, lucide-svelte |
| 배포 | Docker Compose (단일 이미지, `GENSUB_ROLE` 분기) |

### 컨테이너 토폴로지

```
            ┌─────────────────── Docker Compose ───────────────────┐
            │                                                      │
 브라우저 ──┼─ :8000 ──► api (FastAPI)   ◄── gensub-data ──► worker│
            │                    │ SSE               (폴링 루프)   │
            │                    │                                 │
            │                    └─ 정적 서빙: SvelteKit build      │
            └──────────────────────────────────────────────────────┘

gensub-data (named volume):
  ├─ db/jobs.db         (SQLite + backups/)
  ├─ media/<job_id>/    (source.mp4, audio.wav, subtitles.{srt,vtt,ass}, burned.mp4)
  └─ models/            (Whisper 모델 캐시)
```

### 데이터 흐름

```
[브라우저] ─POST /api/jobs─► [api] ─insert─► [SQLite jobs]
                                                │ poll 1.5s
                                                ▼
                                        [worker] ─► download → audio → transcribe
                                                ─► save segments + SRT/VTT
                                                ─► status=ready
                                                ↓ SSE
[브라우저] ◄─── progress / segment_ready / done / error
         │
         ├─ GET /api/jobs/<id>/video            (HTTP Range)
         ├─ GET /api/jobs/<id>/subtitles.vtt    (<track>)
         ├─ PATCH /api/jobs/<id>/segments/<idx> (편집)
         └─ POST /api/jobs/<id>/burn            (→ worker ffmpeg burn-in)
```

---

## 2. 컴포넌트 지도

### 2.1 백엔드 (`backend/`)

```
backend/
├── pyproject.toml          # uv 프로젝트 정의
├── app/
│   ├── main.py             # FastAPI 팩토리, lifespan, SPA fallback
│   ├── core/
│   │   ├── settings.py     # pydantic-settings, 모든 env 여기로
│   │   └── db.py           # engine 생성 + WAL/sync 설정
│   ├── models/
│   │   ├── job.py          # Job, JobStatus enum, SourceKind enum
│   │   └── segment.py      # Segment
│   ├── api/                # 라우터만. services만 호출.
│   │   ├── jobs.py         # POST /jobs, /upload, cancel, delete, pin, burn
│   │   ├── events.py       # SSE
│   │   ├── media.py        # video(Range), subtitles, transcript, mux, burned, clip
│   │   ├── segments.py     # PATCH, search_replace
│   │   ├── config.py       # GET /api/config (프론트 초기값)
│   │   ├── health.py       # GET /api/health
│   │   └── schemas.py      # Pydantic I/O 스키마
│   └── services/           # 도메인 로직. Session 소유.
│       ├── jobs.py         # 작업 생성/취소/삭제/pin/burn 요청
│       ├── job_state.py    # 상태 전이 (mark_ready/failed/done 등)
│       ├── pipeline.py     # process_job / process_burn_job 오케스트레이션
│       ├── downloader.py   # yt-dlp
│       ├── audio.py        # ffmpeg로 wav 추출
│       ├── transcriber.py  # faster-whisper
│       ├── subtitles.py    # SRT/VTT 포매터
│       ├── segments.py     # 세그먼트 CRUD
│       ├── ass_style.py    # burn-in용 ASS
│       ├── burn.py         # ffmpeg burn-in (취소 지원)
│       ├── muxer.py        # mkvmerge
│       ├── clip.py         # 구간 클립 내보내기
│       ├── cleanup.py      # TTL purge + zombie sweep
│       └── backup.py       # DB 백업 (api + worker 공용)
├── worker/
│   └── main.py             # signal handler, poll 루프 (burn 우선)
└── tests/                  # pytest (38개 예상)
```

**레이어 규칙** (상세는 [`CLAUDE.md`](../CLAUDE.md) §2):
- `api/` 라우터는 `services/`만 호출. Session 직접 열기 금지.
- Job 상태 전이는 `services/job_state.py` 전용.
- 파이프라인은 `services/pipeline.py` 소유, 워커는 폴링/dispatch만.

### 2.2 프론트엔드 (`frontend/src/`)

```
src/
├── app.html, app.css
├── routes/
│   ├── +layout.svelte      # 사이드바 + 다크모드 토글 + processing 중 UI lock
│   └── +page.svelte        # current.screen으로 분기
└── lib/
    ├── api/
    │   ├── client.ts       # fetch 래퍼
    │   ├── jobs.ts         # job CRUD + 업로드 + burn
    │   ├── events.ts       # EventSource 구독
    │   └── types.ts        # 백엔드 schemas와 대응
    ├── stores/
    │   ├── current.ts      # {screen, jobId, ...}
    │   └── history.ts      # localStorage 최근 작업 + 서버 동기화
    ├── screens/            # 상태별 화면
    │   ├── IdleScreen.svelte       # 입력/업로드
    │   ├── ProcessingScreen.svelte # 원형 진행률
    │   ├── ReadyScreen.svelte      # Player + SegmentList + 다운로드
    │   ├── ErrorScreen.svelte
    │   ├── BurnDoneScreen.svelte
    │   └── useShortcuts.ts         # 키보드 단축키
    └── ui/                 # 재사용 컴포넌트
        ├── Sidebar.svelte, BurnSheet.svelte, ClipSheet.svelte, BottomSheet.svelte
        ├── CircularProgress.svelte, SegmentList.svelte, EditableSegment.svelte
        ├── VideoPlayer.svelte, DownloadBar.svelte
        ├── Button.svelte, Input.svelte, Segmented.svelte, SearchReplace.svelte
```

---

## 3. Job 상태머신

```
                 cancel?
pending ────────► downloading ────► transcribing ────► ready ──┐
   │                  │                    │            │      │
   │                  │                    │            │  (burn 요청)
   │                  │                    │            ▼      │
   │                  │                    │         burning ──┤
   │                  ▼                    ▼            │      │
   └──────────────► failed ◄────────────────────────────┘      │
                                                               ▼
                                                             done
```

| 상태 | 진입 시점 | 다음 상태 | 관련 파일 |
|---|---|---|---|
| `pending` | 작업 생성 | downloading (worker claim) | `api/jobs.py` POST `/jobs` |
| `downloading` | worker claim + `source_kind=url` | transcribing 또는 failed | `services/pipeline.py`, `services/downloader.py` |
| `transcribing` | 다운로드 완료 (또는 upload 직후) | ready 또는 failed | `services/transcriber.py` |
| `ready` | 전사 완료 + SRT/VTT 저장 | burning (사용자 요청) 또는 terminal | `services/job_state.mark_ready` |
| `burning` | `request_burn()` 호출 | done 또는 failed | `services/jobs.request_burn`, `services/pipeline.process_burn_job` |
| `done` | burn 완료 | terminal | `services/job_state.mark_done` |
| `failed` | 어느 단계든 예외 | terminal (재시도는 새 job) | `services/job_state.mark_failed` |

**취소** (`cancel_requested=True`):
- `process_job`: 각 단계 사이에 `_check_cancel()` → `JobCancelledError` → `mark_failed`
- `process_burn_job`: ffmpeg 진행 루프 매 라인마다 `_check_cancel()` → `proc.terminate()` → `JobCancelledError` → `mark_failed`

**좀비 복구**:
- api 시작 시 `sweep_zombie_jobs`가 `downloading`/`transcribing`/`burning`에서 멈춘 작업을 `failed`로 마킹.

---

## 4. 기능 카탈로그

| 기능 | 프론트 | API | Services |
|---|---|---|---|
| URL로 작업 생성 | `IdleScreen.svelte` | `POST /api/jobs` | `services/jobs.create_url_job` |
| 파일 업로드 작업 | `IdleScreen.svelte` (드래그) | `POST /api/jobs/upload` | `services/jobs.create_upload_job` |
| 진행률 구독 | `ProcessingScreen.svelte` | `GET /api/jobs/<id>/events` (SSE) | (라우터 내부) |
| 영상 스트리밍 | `VideoPlayer.svelte` | `GET /api/jobs/<id>/video` (Range) | `api/media.video` |
| VTT 자막 트랙 | `VideoPlayer.svelte` `<track>` | `GET /api/jobs/<id>/subtitles.vtt` | `services/subtitles` |
| 세그먼트 리스트 | `SegmentList.svelte` | `GET /api/jobs/<id>/segments` | `services/segments.load_segments` |
| 세그먼트 텍스트 편집 | `EditableSegment.svelte` | `PATCH /api/jobs/<id>/segments/<idx>` | `services/segments.update_text` |
| 자막 파일 다운로드 | `DownloadBar.svelte` | `GET .../subtitles.srt`, `.vtt`, `transcript.txt`, `.json` | `services/subtitles`, `services/segments` |
| MKV mux 다운로드 | `DownloadBar.svelte` | `GET .../download/video+subs.mkv` | `services/muxer` |
| Burn-in 요청 | `BurnSheet.svelte` | `POST /api/jobs/<id>/burn` | `services/jobs.request_burn` → worker `services/pipeline.process_burn_job` |
| Burn 결과 다운로드 | `BurnDoneScreen.svelte` | `GET .../download/burned.mp4` | `api/media.burned` |
| 구간 클립 내보내기 | `ClipSheet.svelte` | `POST .../clip` | `services/clip` |
| 작업 취소 | 각 화면 | `POST /api/jobs/<id>/cancel` | `services/jobs.cancel_job` |
| 작업 삭제 | `Sidebar.svelte` | `DELETE /api/jobs/<id>` | `services/jobs.delete_job` |
| 북마크(pin) | `Sidebar.svelte` | `POST /api/jobs/<id>/pin` | `services/jobs.pin_job` |
| 최근 작업 목록 | `Sidebar.svelte` | (localStorage + `GET /api/jobs/<id>`) | `stores/history.ts` |
| 다크/라이트 모드 | `+layout.svelte` | - | `theme.ts` + localStorage |
| 키보드 단축키 | `ReadyScreen.svelte` | - | `useShortcuts.ts` |

---

## 5. 데이터 모델 + API

### 5.1 SQLite 스키마

**`Job`** (`models/job.py`) — 작업 단위. `id`는 UUID4 문자열. 주요 필드:
- `source_url`, `source_kind` (`url`|`upload`), `title`, `duration_sec`, `language`, `model_name`, `initial_prompt`.
- `status` (JobStatus enum), `progress` (0.0~1.0), `stage_message`, `error_message`.
- `created_at`, `updated_at`, `expires_at`, `cancel_requested`, `pinned`.

**`Segment`** (`models/segment.py`) — 세그먼트. `(job_id, idx)` 고유. `start/end` 초 단위. `avg_logprob`·`no_speech_prob`·`words` (word-level JSON)은 편집 및 저신뢰도 하이라이트용.

### 5.2 REST 엔드포인트 요약

| Method | Path | 역할 |
|---|---|---|
| POST | `/api/jobs` | URL 작업 생성 |
| POST | `/api/jobs/upload` | 파일 업로드 작업 생성 |
| GET | `/api/jobs/{id}` | 작업 조회 |
| GET | `/api/jobs/{id}/events` | SSE 진행률 스트림 |
| POST | `/api/jobs/{id}/cancel` | 취소 요청 |
| POST | `/api/jobs/{id}/pin` | 북마크 토글 |
| POST | `/api/jobs/{id}/burn` | Burn-in 시작 |
| DELETE | `/api/jobs/{id}` | 즉시 삭제 |
| GET | `/api/jobs/{id}/video` | 영상 Range 스트리밍 |
| GET | `/api/jobs/{id}/subtitles.vtt` \| `.srt` | 자막 |
| GET | `/api/jobs/{id}/transcript.txt` \| `.json` | 텍스트 export |
| GET | `/api/jobs/{id}/download/video+subs.mkv` | MKV mux |
| GET | `/api/jobs/{id}/download/burned.mp4` | Burn 결과 |
| POST | `/api/jobs/{id}/clip` | 구간 클립 요청 |
| GET | `/api/jobs/{id}/segments` | 세그먼트 리스트 |
| PATCH | `/api/jobs/{id}/segments/{idx}` | 세그먼트 편집 |
| POST | `/api/jobs/{id}/search_replace` | 전체 찾아바꾸기 |
| GET | `/api/config` | 프론트 초기값 (모델 목록, ttl, max_video 등) |
| GET | `/api/health` | 헬스체크 |

---

## 6. 배포·운영

### 6.1 Docker 구성

- 단일 이미지 (`gensub:latest`). 두 컨테이너(`api`, `worker`)가 같은 이미지에 다른 `GENSUB_ROLE` env로 기동.
- 빌드: `node:22-slim` 스테이지에서 SvelteKit build → `python:3.11-slim` 스테이지에 `--from=frontend-build ... ./app/static`로 복사.
- ffmpeg, mkvtoolnix, libsndfile1, procps, curl 설치.
- 프론트 정적 파일 서빙은 api 프로세스가 SPA fallback과 함께 담당.

### 6.2 볼륨

Named volume **`gensub-data`** 하나에 `/data/{db,media,models}` 전부 담김. bind mount 대신 named volume을 쓰는 이유는 호스트 FS 레이아웃과 분리 + 컨테이너 재생성 시 데이터 보존.

### 6.3 Healthcheck

- `api`: `curl -fsS http://localhost:8000/api/health` (30s 간격).
- `worker`: `pgrep -f worker.main` (30s 간격). `procps`가 이미지에 포함돼 있음.

### 6.4 DB 백업

- `services/backup.py`의 `backup_database()`가 api + worker 양쪽 기동 시점에 호출.
- 백업 위치: `{db_dir}/backups/jobs_YYYYMMDD_HHMMSS.db`. 최근 3개 유지, 초과분 자동 삭제.

### 6.5 정리 작업

- api 기동 시 `sweep_zombie_jobs` 실행 (진행 중 상태 → failed).
- api 기동 후 백그라운드 태스크가 1시간마다 `purge_expired_jobs` 실행 (`expires_at < now`이며 `pinned=False`인 작업 DB 레코드 + 미디어 디렉토리 삭제).

---

## 7. 확장 지점

### 새 자막 포맷 추가

1. `services/subtitles.py`에 `format_xxx(segments) -> str` 함수.
2. `api/media.py`에 엔드포인트 추가 (`GET /api/jobs/{id}/subtitles.xxx`).
3. `frontend/src/lib/ui/DownloadBar.svelte`에 다운로드 칩.
4. 테스트 추가.

### 다른 STT 백엔드 추가 (예: whisper.cpp)

1. `services/transcriber.py`를 인터페이스로 분리 (현재는 faster-whisper만).
2. 구현체 추가.
3. `settings.py`에 `STT_BACKEND` env.
4. `services/pipeline.py`에서 분기.

### 새 화면 상태 추가

1. `models/job.py`의 `JobStatus`에 값 추가.
2. `services/job_state.py`에 전이 함수.
3. 프론트 `stores/current.ts`의 `screen` 타입 확장.
4. `screens/`에 새 컴포넌트.
5. 이 문서의 §3 상태머신 다이어그램 업데이트.

---

## 8. 참고 문서

- [초기 설계 스펙](superpowers/specs/2026-04-11-gensub-design.md) — 설계 의도 (2026-04-11)
- [안정성 리팩토링 스펙](superpowers/specs/2026-04-18-stability-refactor-design.md) — 본 문서가 반영하는 리팩토링 (2026-04-18)
- [개발 규약](../CLAUDE.md)
````

- [ ] **Step 2: 커밋**

```bash
git add docs/architecture.md
git commit -m "$(cat <<'EOF'
docs: add architecture.md describing current system state

백엔드/프론트 컴포넌트 지도, Job 상태머신, 기능 카탈로그
(사용자 관점 기능 × 관련 파일), 데이터 모델 + API 엔드포인트 요약,
배포·운영(Docker, 볼륨, healthcheck, 백업, 정리), 확장 지점 가이드.
Phase 3 리팩토링 이후 구조를 미리 반영.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2.4: `README.md` 덮어쓰기

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 현재 README 백업 (참고용 임시)**

```bash
cd /Users/loki/GenSub
cat README.md > /tmp/readme-before.md
wc -l /tmp/readme-before.md
```

Expected: ~30줄 내외 (quickstart 중심 짧은 문서).

- [ ] **Step 2: 새 README 작성**

Write `README.md`:

````markdown
# GenSub

YouTube 영상이나 로컬 파일을 받아 **Whisper로 자막을 만들고 브라우저에서 편집·시청·다운로드**할 수 있는 자체 호스팅 웹 서비스. `docker compose up` 한 번으로 구동.

![GenSub 시작 화면](docs/images/gensub-idle-screen.png)

---

## 핵심 기능

- 📥 **YouTube URL 또는 로컬 파일** — yt-dlp로 가져오거나 드래그 앤 드롭 업로드
- 🎙 **Whisper 기반 로컬 자막 생성** — faster-whisper(CPU int8 / GPU float16), 언어 자동감지 + 수동 지정, 한·영 혼합 code-switch 모드
- ✏️ **브라우저 편집기** — 세그먼트 단위 인플레이스 텍스트 편집, 클릭 투 점프, 키보드 단축키
- 💾 **5가지 내보내기** — SRT / VTT / TXT / JSON / MKV(mkvmerge mux)
- 🔥 **Burn-in MP4** — 자막을 구운 MP4 + 특정 구간만 클립 내보내기
- 🌙 **다크/라이트 모드** — 시스템 자동 감지 + 수동 토글, 한국어 UI
- 🔖 **최근 작업 + 북마크** — TTL 자동 정리, 북마크한 작업은 보호

![GenSub 편집 화면](docs/images/gensub-final-ready.png)

---

## 아키텍처 (한 줄 요약)

FastAPI API + Python 워커(같은 이미지, `GENSUB_ROLE`로 분기) + SQLite 작업 큐 + SvelteKit SPA. 진행률은 SSE, 영상은 HTTP Range 스트리밍.

```
[브라우저] ─► api (FastAPI + SvelteKit static) ◄── SQLite ──► worker (yt-dlp + Whisper + ffmpeg)
                         │ SSE
                         └─► 브라우저
```

자세한 건 [`docs/architecture.md`](docs/architecture.md).

---

## 빠른 시작

```bash
git clone <repo-url>
cd GenSub
cp .env.example .env   # 필요하면 수정
docker compose up -d
open http://localhost:8000
```

첫 실행 시 Whisper 모델이 자동 다운로드됩니다 (small ≈ 500MB, large-v3 ≈ 3GB). 이후에는 `gensub-data` volume에 캐시됩니다.

---

## 요구사항

- **Docker 20+**, Docker Compose v2+
- 디스크 여유 공간: 모델(~3GB까지) + 작업 미디어 (영상 길이 x 2~3배)
- Apple Silicon(M1~M4) Mac 또는 Intel/AMD Linux. GPU는 선택(float16 모드).

---

## 주요 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `GENSUB_PORT` | `8000` | 호스트 접속 포트 |
| `JOB_TTL_HOURS` | `24` | 작업 파일 자동 삭제까지 시간 |
| `MAX_VIDEO_MINUTES` | `90` | 허용 최대 영상 길이 |
| `DEFAULT_MODEL` | `small` | `tiny`/`base`/`small`/`medium`/`large-v3` |
| `COMPUTE_TYPE` | `int8` | CPU=`int8`, NVIDIA GPU=`float16` |
| `WORKER_CONCURRENCY` | `1` | 동시 작업 수 (상한 권장 4) |
| `OPENAI_API_KEY` | `""` | 옵션: OpenAI Whisper API 폴백 |

전체 목록은 `.env.example` 참고.

---

## 개발

핫 리로드 모드:

```bash
cp compose.override.yaml.example compose.override.yaml
docker compose up
```

백엔드 테스트:

```bash
cd backend
uv run pytest
```

코드/문서 규약은 [`CLAUDE.md`](CLAUDE.md) 참고.

---

## 문서

- [`docs/architecture.md`](docs/architecture.md) — 현재 아키텍처
- [`CLAUDE.md`](CLAUDE.md) — 개발 규약
- [`docs/superpowers/specs/`](docs/superpowers/specs/) — 설계 스펙 히스토리
- [`docs/superpowers/plans/`](docs/superpowers/plans/) — 구현 플랜

---

## 라이선스

(프로젝트 상황에 맞춰 추가)
````

- [ ] **Step 3: 커밋**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs: rewrite README as project introduction + quickstart

기존 최소한의 quickstart에서 확장: 한 줄 소개 + 스크린샷 2장 +
기능 불릿 + 간단 아키텍처 요약 + quickstart + 요구사항 + env 표 +
개발 모드 + 문서 링크. architecture.md / CLAUDE.md 연결.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Phase 2 완료 검증

- [ ] **Step 1: 문서 3개 존재 확인**

```bash
cd /Users/loki/GenSub
ls -la CLAUDE.md docs/architecture.md README.md docs/images/gensub-*.png
```

Expected: 4개 파일 모두 존재 (CLAUDE, architecture, README, 2개 PNG).

- [ ] **Step 2: 루트 스크린샷 정리 확인**

```bash
ls gensub-*.png 2>/dev/null | wc -l
```

Expected: 0.

- [ ] **Step 3: 커밋 히스토리 확인**

```bash
git log --oneline -5
```

Expected: 최근 4개 커밋이 본 Phase의 작업.

Phase 2 완료. Phase 3 리팩토링 진행 가능.
