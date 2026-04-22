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
| 최근 작업 목록 | `Sidebar.svelte` 영상 탭 | (localStorage + `GET /api/jobs`) | `stores/history.ts`, `services/jobs.list_recent_jobs` |
| 세그먼트 메모 저장/해제 | `SegmentMemo.svelte` | `POST /api/jobs/<id>/segments/<idx>/memo` | `services/memo.toggle_save_memo` |
| 메모 텍스트 수정 | `SegmentMemo.svelte` (인라인 textarea) | `PATCH /api/memos/<id>` | `services/memo.update_memo_text` |
| 전역 메모 리스트 | `Sidebar.svelte` 메모 탭 + `MemoCard.svelte` | `GET /api/memos` | `services/memo.list_all_memos_with_liveness` |
| Job별 메모 조회 | `jobMemos` store (SegmentList 표시용) | `GET /api/jobs/<id>/memos` | `services/memo.list_memos_for_job` |
| 메모 삭제 | `MemoCard.svelte` 삭제 버튼 | `DELETE /api/memos/<id>` | `services/memo.delete_memo` |
| 보러가기 (메모→영상) | `openMemo` + `ReadyScreen` reactive seek | - | `stores/current.ts` (initialTime) |
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

**`Memo`** (`models/memo.py`) — 세그먼트 단위 저장 + 선택적 사용자 메모. `UNIQUE(job_id, segment_idx)`. `memo_text` 빈 문자열 허용(메모 없이 북마크 가능). 스냅샷 필드(`segment_text_snapshot`, `segment_start`, `segment_end`, `job_title_snapshot`)로 Job/Segment 만료 시에도 리스트에 텍스트 보존. 생성 시 `services/memo.toggle_save_memo` 가 해당 Job을 자동 pin.

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
| GET | `/api/jobs` | 사이드바용 최근 Job 리스트 (pinned 우선, 만료돼도 pinned 보존) |
| POST | `/api/jobs/{id}/segments/{idx}/memo` | 메모 toggle-save (201 create / 200 delete / 409 has-text / 404) |
| GET | `/api/jobs/{id}/memos` | Job별 메모 lite 리스트 (segment UI 상태 표시용) |
| GET | `/api/memos` | 전역 메모 리스트 (최신순, `job_alive` 포함) |
| PATCH | `/api/memos/{id}` | 메모 텍스트 수정 (500자 제한) |
| DELETE | `/api/memos/{id}` | 메모 삭제 |
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
