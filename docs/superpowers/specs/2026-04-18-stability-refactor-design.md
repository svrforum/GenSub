# GenSub 안정성 리팩토링 + 문서 정비 설계 명세

**날짜**: 2026-04-18
**프로젝트**: GenSub
**목적**: 111커밋 축적된 현재 구현을 유지·확장 가능한 상태로 정리하고, 개발 규약·아키텍처·프로젝트 소개 문서 체계를 세운다.
**스펙 성격**: 변경 제안 (리팩토링 + 문서 신설/개편). 이번 작업이 끝나면 "현재 상태"는 새로 생성될 `docs/architecture.md`로 이관된다.

---

## 1. 배경과 동기

### 1.1 현재 저장소 상태

- `master` (3커밋): 초기 설계 스펙 `docs/superpowers/specs/2026-04-11-gensub-design.md`, 16개 phase 플랜.
- `feature/gensub` (`.worktrees/gensub-impl`, 111커밋): 실제 구현 전체 (백엔드 FastAPI + 워커 + SvelteKit 프론트 + Docker 스택).

두 브랜치가 장시간 분리된 채 운영돼, master는 "설계 시점", feature/gensub는 "최신 운영 상태"라는 부조화가 존재한다.

### 1.2 안정성 감사 결과 요약 (2026-04-18 수행)

High 신뢰도 이슈 4건, Medium 6건. 전체 구조는 이미 견고 (SQLite WAL·취소 전파·파일 생명주기 분리·SSE cleanup 모두 건전). 리팩토링은 "경계 정리 + 특정 경로 보강 + 죽은 코드 제거" 범위로 충분.

#### High 신뢰도 이슈 (전부 본 스펙 범위에 포함)

| ID | 이슈 |
|---|---|
| H1 | `regenerate` 엔드포인트·서비스가 프론트에서 호출되지 않음 — 죽은 코드. 동기 HTTP에서 ffmpeg+Whisper 실행(잠재 DoS) |
| H2 | `api/jobs.py`의 `pin_job`·`trigger_burn`이 `services/` 경유 없이 라우터 안에서 직접 `Session`을 열고 도메인 로직 수행 — 레이어 경계 혼탁 |
| H3 | `process_burn_job`에 cancel 체크 없음 — burn 중 취소 시 ffmpeg가 끝날 때까지 큐가 막힘 |
| H4 | Sidebar의 `ttlDays` 설정이 백엔드로 전송되지 않음 — 사용자는 "7일 보관" 선택해도 서버는 24시간 후 삭제 (UX 버그) |

#### Medium (본 스펙 범위에 포함되는 3건)

| ID | 이슈 |
|---|---|
| M1 | `burn.py:43`의 `assert proc.stdout is not None` — 프로덕션에서 `-O` 플래그 시 제거됨 |
| M2 | `_backup_db`이 `app/main.py`의 lifespan inline에만 존재 — API가 기동되지 않은 채 worker만 돌다 크래시 시 백업 누락 |
| M3 | `compose.yaml`의 worker에 healthcheck 없음 |

#### Medium (본 스펙 제외, "다음 기회")

- `claim_next_pending_job`의 수동 `BEGIN IMMEDIATE` vs `engine.begin()` 패턴 — 현재 동작 검증됨
- SSE 연결 종료 감지 0.5초 지연 — 체감 영향 없음
- `SegmentList`의 `editingIdx` ↔ `selectedIndices` 충돌 — 재현 경로 불명확

---

## 2. Goals / Non-Goals

### Goals

1. 레이어 경계(라우터 → 서비스 → 모델)를 규칙으로 명문화하고, 위반하는 2곳을 수정한다.
2. burn 파이프라인에 취소 경로를 추가해 큐 블로킹을 제거한다.
3. 프론트 설정과 백엔드 설정의 단절(ttlDays)을 해소한다.
4. 죽은 코드(`regenerate`)와 표류 아티팩트(루트 스크린샷 41장)를 정리한다.
5. 운영 안정성 보강: worker healthcheck, 백업 서비스 분리, `assert` → 명시적 예외.
6. 개발 규약(`CLAUDE.md`) · 현재 아키텍처(`docs/architecture.md`) · 프로젝트 소개(`README.md`) 세 문서 축을 세운다.
7. `feature/gensub` → `master` 머지로 저장소 상태를 정상화한다.

### Non-Goals

- 신규 기능 추가. 기존 기능의 재구성·제거만 수행한다.
- 데이터베이스 스키마 변경. 상태머신, Job/Segment 모델은 그대로.
- Whisper 엔진 교체(whisper.cpp 등)나 Redis 큐 도입 같은 아키텍처 전환.
- 프론트엔드 테스트 프레임워크 도입 — 이번 스코프에서는 백엔드 테스트만 추가한다. (별도 스펙 대상)
- Medium 이슈 중 제외한 3건 — 본 스펙에서 다루지 않는다.

---

## 3. 작업 전체 지도

```
┌────────────────────────────────────────────────────────────┐
│ Phase 1: Git 정리 │
│ feature/gensub → master 일반 merge (히스토리 보존) │
│ .worktrees/gensub-impl 제거 │
│ refactor/stability 브랜치 생성 │
├────────────────────────────────────────────────────────────┤
│ Phase 2: 문서 작성 (서로 독립) │
│ docs/architecture.md (신규, 현재 상태 기록) │
│ CLAUDE.md (신규, 개발·에이전트 규약) │
│ README.md (덮어쓰기, 프로젝트 소개) │
│ 루트 스크린샷 정리 (2장 유지, 39장 삭제) │
├────────────────────────────────────────────────────────────┤
│ Phase 3: 리팩토링 R1 → R7 (작은 것부터) │
│ R1 regenerate 제거 │
│ R5 assert → RuntimeError │
│ R7 worker healthcheck │
│ R2 pin_job / trigger_burn 서비스 추출 │
│ R4 ttlDays 프론트↔백엔드 연결 │
│ R6 백업 서비스 분리 + worker 호출 │
│ R3 burn 취소 경로 (+ ffmpeg 프로세스 종료) │
├────────────────────────────────────────────────────────────┤
│ Phase 4: 통합 검증 │
│ pytest 전체 / docker compose build / 수동 smoke │
├────────────────────────────────────────────────────────────┤
│ Phase 5: 완료 │
│ refactor/stability → master 머지 │
│ 구 설계 스펙 상단에 "현재 상태는 architecture.md" 안내 │
└────────────────────────────────────────────────────────────┘
```

예상 소요: 2~3세션.

---

## 4. Phase 1 — Git 정리

### 4.1 머지 전략

**일반 merge** (squash 아님) — 111커밋의 반복 개선 이력을 자산으로 본다.

```
# master에서
git merge --no-ff feature/gensub -m "merge: integrate feature/gensub (111 commits of iterative implementation)"
git worktree remove .worktrees/gensub-impl
# feature/gensub 브랜치는 삭제하지 않고 참조용으로 보존 (롤백 경로)
git checkout -b refactor/stability
```

### 4.2 머지 후 상태 검증 체크포인트

- `git log --oneline | wc -l` ≥ 114
- `backend/`, `frontend/`, `compose.yaml`, `Dockerfile` 등 구현물이 master에 존재
- `docs/superpowers/specs/2026-04-11-gensub-design.md` 기존 파일 그대로 존재
- 본 스펙 파일(`2026-04-18-…design.md`)도 merge 결과에 포함

### 4.3 실패 시 롤백

머지 후 문제 발견 시 `git reset --hard ORIG_HEAD`로 복구 가능. worktree는 머지 전까지 그대로 둬서 롤백 경로를 열어둔다.

---

## 5. Phase 2 — 문서 3종

### 5.1 `docs/architecture.md` (신규, 예상 ~400줄)

**역할**: 현재 구현된 시스템의 "현재 상태" 설명 문서. "앞으로 만들 것"이 아니라 "지금 있는 것"을 정확히 기록. 새로 합류하는 개발자 또는 3개월 후의 자신이 한 번에 전체 그림을 파악하게 만드는 것이 목표.

**섹션 구성**:

1. **한눈에 보기** — 한 단락 프로젝트 정의 + 기술 스택 표 + 데이터 흐름 ASCII 다이어그램
2. **컴포넌트 지도** — 백엔드/프론트엔드 디렉토리별 책임
 - `backend/app/api/` — REST/SSE 라우터. services만 호출.
 - `backend/app/services/` — 도메인 로직. Session 소유.
 - `backend/app/models/` — SQLModel 엔티티.
 - `backend/app/core/` — settings, DB 엔진.
 - `backend/worker/` — 폴링 루프, pipeline 오케스트레이션.
 - `frontend/src/lib/api/` — HTTP/SSE 클라이언트.
 - `frontend/src/lib/stores/` — current(상태머신) + history(localStorage 동기화).
 - `frontend/src/lib/screens/` — 상태별 화면.
 - `frontend/src/lib/ui/` — 재사용 컴포넌트.
3. **Job 상태머신 + 파이프라인**
 - 상태 다이어그램 (pending → downloading → transcribing → ready → burning → done / failed)
 - 각 상태 전이에서 일어나는 일 + 관련 파일 참조
 - 취소 경로 (`cancel_requested` → `_check_cancel`)
4. **기능 카탈로그** — 기능 × 관련 파일 표. 사용자 관점의 기능명 → 백엔드 엔드포인트, 프론트 컴포넌트.
5. **데이터 모델 + API 요약** — Job/Segment 스키마 + 엔드포인트 일람 (상세는 코드 참조).
6. **배포·운영** — Docker 구성, 볼륨(named volume `gensub-data`), healthcheck, DB 백업, TTL 정리, 좀비 복구.
7. **확장 지점** — 새 자막 포맷 추가·다른 STT 백엔드 도입·새 화면 추가 시 손봐야 하는 지점.

**작성 원칙**:
- 설계 의도("왜 이렇게 만들었나")는 구 스펙에 남기고, 본 문서는 "지금 어떻게 되어 있나"에 집중.
- 파일 경로는 코드 기준 그대로 — 구조 변경 시 이 문서도 업데이트되는 것이 원칙.

### 5.2 `CLAUDE.md` (신규, 루트, 예상 ~180줄)

**역할**: 개발 에이전트가 세션마다 자동으로 읽는 규약 파일. 사람·AI 공통 개발 룰.

**섹션 구성**:

1. **프로젝트 한 단락 소개** — GenSub이 뭐고 스택은 뭔지.
2. **코드 컨벤션**
 - Python: Python 3.11+, 타입 힌트 필수(단, 테스트 제외), ruff 규칙(E/F/I/N/UP/B/SIM), 100자 라인 제한.
 - Svelte/TS: `strict: true`, 컴포넌트 파일 300줄 초과 시 분리 검토, `<script lang="ts">` 기본.
3. **아키텍처 규칙 (위반 시 레이어 경계 깨짐)**
 - `api/` 라우터 안에서 `Session(engine)` 직접 열기 금지 → `services/` 함수 호출.
 - Job 상태 전이는 반드시 `services/job_state.py` 경유.
 - 파이프라인 단계 추가/수정은 `services/pipeline.py`에 국한, 워커 폴링 로직 건드리지 않는다.
 - 설정은 `app/core/settings.py` `Settings`에만 추가. 하드코딩된 env 참조 금지.
4. **테스트 규칙**
 - `backend/tests/test_<module>.py` 네이밍.
 - 새 서비스/엔드포인트 추가 시 테스트 동반. `pytest-asyncio` mode=auto.
 - 리팩토링 시작 전 `uv run pytest` 그린 확인.
5. **커밋/브랜치 규칙**
 - 컨벤셔널 커밋(`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`).
 - 커밋 메시지는 **왜** 중심.
 - 리팩토링은 별도 브랜치(`refactor/*`)에서.
 - 머지 커밋 메시지에 요약 포함.
6. **에이전트(에이전트 동작 규약**
 - **모델 = 고정**. `Agent` tool 호출 시 `model: "opus"` 명시.
 - 모든 리팩토링 작업 전 `uv run pytest`로 기존 테스트 그린 확인.
 - 경로는 항상 절대경로 사용.
 - worktree가 필요한 경우 `superpowers:using-git-worktrees` 가이드 참조.
 - 문서 경로 규칙:
 - `docs/architecture.md` = **현재 상태** (코드와 동기화).
 - `docs/superpowers/specs/YYYY-MM-DD-*.md` = **변경 제안** (시간 스냅샷, 보존).
 - `docs/superpowers/plans/*/` = 실행 플랜 (체크리스트).
 - `CLAUDE.md` = 규약 (이 파일).
 - `README.md` = 외부 독자용 소개.
7. **위반 시 대처** — 본 파일과 충돌하는 요청을 받으면 먼저 파일의 업데이트를 제안한다.

### 5.3 `README.md` (덮어쓰기, 예상 ~130줄)

**역할**: GitHub 방문자와 첫 사용자를 위한 간결한 소개·퀵스타트.

**섹션 구성**:

1. 타이틀 + 한 줄 소개.
2. 스크린샷 (idle 화면) — `docs/images/gensub-idle-screen.png`.
3. **핵심 기능** (불릿 6~8개):
 - YouTube URL / 로컬 파일 업로드
 - Whisper 기반 로컬 자막 생성 (언어 자동감지 + 수동지정, 한영 혼합 모드)
 - 브라우저에서 세그먼트 단위 시청·편집
 - SRT/VTT/TXT/JSON/MKV mux 다운로드
 - ffmpeg burn-in 영상 내보내기 + 구간 클립
 - 다크/라이트 모드, 한국어 UI
 - 최근 작업 북마크 + TTL 자동 정리
4. 스크린샷 (ready 화면) — `docs/images/gensub-final-ready.png`.
5. **아키텍처 개요** — 3줄 요약 + 간단 다이어그램(api/worker/SQLite).
6. **Quickstart**: `docker compose up -d`.
7. **요구사항**: Docker, 디스크 용량, 지원 OS.
8. **개발**: `compose.override.yaml.example` → `compose.override.yaml` 복사, 핫 리로드.
9. **문서 링크**: architecture / CLAUDE / 구 설계 스펙.
10. **라이선스 · 기타**: 짧게.

---

## 6. Phase 2 부가 — 스크린샷 정리

- 유지(두 장): `gensub-idle-screen.png`, `gensub-final-ready.png` → `docs/images/`로 이동.
- 삭제(39장): 나머지 전부. Playwright 세션 아티팩트라 필요 시 재생성 가능.
- `.gitignore`에 `/gensub-*.png` 패턴 추가 — 앞으로 루트에 스크린샷이 실수로 쌓이지 않도록 방지. (이미 `.playwright-mcp/`는 제외됨.)

---

## 7. Phase 3 — 리팩토링 상세

### R1. `regenerate` 엔드포인트 · 서비스 제거 (Small)

**이유**: 프론트 호출 경로 없음. 동기 HTTP 내 ffmpeg+Whisper 실행은 API 프로세스 블로킹 + 잠재 DoS. 재도입 시에는 worker queue 경유로 재설계 필요.

**변경**:
- 삭제: `backend/app/services/regenerate.py`
- 삭제: `backend/tests/test_regenerate.py`
- 수정: `backend/app/api/segments.py` — `POST /{job_id}/segments/{idx}/regenerate` 라우트 제거
- 수정: `frontend/src/lib/api/jobs.ts` — `regenerateSegment` 함수 제거
- 수정: `frontend/src/lib/api/types.ts` — 관련 타입 제거 (있다면)

**검증**: 전체 테스트 그린, 프론트 빌드 성공.

### R2. `pin_job` · `trigger_burn` 서비스 레이어 추출 (Small)

**이유**: 두 엔드포인트만 라우터에서 직접 Session을 열고 도메인 로직 실행 중. `cancel_job`/`delete_job`은 이미 서비스 경유 — 일관성 없음.

**변경**:
- `backend/app/services/jobs.py`에 함수 신설:
 - `pin_job(engine, job_id, pinned: bool) -> None`
 - `request_burn(engine, job_id) -> None` — 상태를 `burning`으로, `progress=0.0`, `stage_message` 설정
- `backend/app/api/jobs.py`:
 - `pin_job` 엔드포인트 → `services.jobs.pin_job()` 호출만 수행
 - `trigger_burn` 엔드포인트 → `services.jobs.request_burn()` 호출만 수행
 - Session 직접 사용 제거
- 테스트 신규:
 - `backend/tests/test_jobs_service_pin.py`
 - `backend/tests/test_jobs_service_request_burn.py`

**검증**: 기존 엔드포인트 통합 테스트도 그린 유지.

### R3. burn 파이프라인 취소 경로 (Medium)

**이유**: burn 중 취소 요청 시 ffmpeg가 수 분 동안 계속 실행 → 다음 작업 대기. `cancel_requested` 플래그는 기록되나 무시됨.

**변경**:
- `backend/app/services/burn.py`:
 - `burn_video()`에 `cancel_check: Callable[[], None] | None` 인자 추가
 - **현재 구조 유지**: `subprocess.Popen`으로 기동한 뒤 `for raw in proc.stdout` 라인 루프로 진행률을 읽는 기존 구조를 그대로 사용.
 - 루프 **매 라인마다** `cancel_check()` 호출. 취소 예외 발생 시 `proc.terminate()` → `proc.wait(timeout=5)` → 타임아웃이면 `proc.kill()` → 원래 예외 재발생.
 - 부분 생성된 `output` 파일 정리는 호출부(`process_burn_job`)에서 담당.
- `backend/app/services/pipeline.py`:
 - `process_burn_job`에 `_check_cancel` 포인트 3군데 추가 (시작 전, 루프 안, 파일 정리 전)
 - `JobCancelledError` 잡아서 `mark_failed("사용자가 작업을 취소했어요")` 처리 (기존 `process_job`과 동일 패턴)
 - 실패 시 부분 생성된 `burned.mp4` 정리
- 테스트 신규: `backend/tests/test_pipeline_burn_cancel.py`
 - 취소 플래그 세팅 후 `process_burn_job` 실행 → `failed` 상태 + 파일 없음 검증
 - ffmpeg 종료 경로는 short fake ffmpeg로 대체하거나 mock

**검증**: 기존 burn 테스트들 그린 유지.

### R4. Sidebar `ttlDays` ↔ 백엔드 `job_ttl_hours` 연결 (Small)

**이유**: 현재 UI는 localStorage에만 저장, 백엔드와 완전 단절 → UX 버그.

**설계 결정**: 서버의 `JOB_TTL_HOURS`는 env로만 설정 가능(런타임 변경 불가). 따라서 UI는 **설정이 아니라 표시**로 역할을 바꾼다.

**변경**:
- `frontend/src/lib/api/jobs.ts` (또는 별도 `config.ts`):
 - `fetchConfig()` — `GET /api/config` 호출, `job_ttl_hours` 포함 반환
- `frontend/src/lib/ui/Sidebar.svelte`:
 - `onMount`에서 `fetchConfig()` 호출해 `job_ttl_hours` 값 로드
 - "보관 기간" 섹션을 **선택형 → 표시형**으로 변경: "현재 서버 설정: N시간 후 자동 삭제" (N은 서버 값)
 - 기존 `localStorage` 키 `gensub.settings.ttlDays`는 **읽지 않고 쓰지 않음**. 남은 값은 다음 localStorage cleanup에서 자연 제거되도록 방치(명시적 삭제 코드는 넣지 않아 다른 기기·탭 영향 없음).
 - 즐겨찾기(pin) 기능 안내 문구 유지: "북마크한 작업은 만료되지 않아요"
- `backend/app/api/config.py`:
 - 변경 없음. 현재 응답에 `job_ttl_hours`가 이미 포함돼 있음 (확인 완료).

**검증**: 프론트 빌드 + 백엔드 config 엔드포인트 응답 스냅샷 검증 테스트.

### R5. `burn.py` `assert` → `RuntimeError` (XS)

**변경**: `backend/app/services/burn.py:43`
- `assert proc.stdout is not None` → `if proc.stdout is None: raise RuntimeError("ffmpeg process failed to start")`

### R6. 백업 로직을 서비스로 분리 + worker 호출 (Small)

**변경**:
- 신규: `backend/app/services/backup.py`
 - `backup_database(settings: Settings) -> None` — 현재 `_backup_db` 로직 이관
 - 최근 3개 유지 상수를 함수 기본값으로
- `backend/app/main.py`:
 - inline `_backup_db` 제거, `services.backup.backup_database(settings)` 호출
- `backend/worker/main.py`:
 - worker 기동 시에도 `backup_database(settings)` 호출
- 테스트 신규: `backend/tests/test_backup.py` — 최근 3개 유지 검증

### R7. worker healthcheck 추가 (XS)

**변경 1 — Dockerfile**: `python:3.11-slim`에는 `pgrep`이 없음(확인 완료). apt 설치 목록에 `procps` 추가:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
 ffmpeg \
 mkvtoolnix \
 libsndfile1 \
 procps \ # 추가
 ca-certificates \
 curl \
 && rm -rf /var/lib/apt/lists/*
```

**변경 2 — `compose.yaml`** worker 서비스에 healthcheck 추가:
```yaml
healthcheck:
 test: ["CMD", "pgrep", "-f", "worker.main"]
 interval: 30s
 timeout: 5s
 retries: 3
```

---

## 8. Phase 4 — 통합 검증

체크리스트:
- [ ] `cd backend && uv run pytest` — 전체 그린 (기대 테스트 수: 35 − 1(삭제) + 4(추가) = 38)
- [ ] `docker compose build` — 빌드 성공
- [ ] `docker compose up -d` → `/api/health` 200
- [ ] 수동 smoke: 짧은 YouTube 링크 하나로 전체 파이프라인 1회 관통 (다운로드 → 전사 → ready → burn → 다운로드)
- [ ] burn 도중 취소 눌러 실제로 10초 내 failed 전이하는지 확인
- [ ] Sidebar에서 "보관 기간" 표시가 24시간으로 뜨는지

---

## 9. Phase 5 — 완료 처리

1. `refactor/stability` → `master` 일반 머지 (Phase 1과 동일한 `--no-ff` 전략)
2. 구 설계 스펙 `docs/superpowers/specs/2026-04-11-gensub-design.md` 최상단에 다음 헤더 추가:

 ```markdown
 > ℹ️ **이 문서는 2026-04-11 시점의 초기 설계 명세**입니다. 현재 구현된 아키텍처는
 > [`docs/architecture.md`](../../architecture.md)를 참고하세요. 본 문서는 설계 의도 보존을 위해 유지됩니다.
 ```
3. 본 스펙(`2026-04-18-…design.md`)도 "완료됨" 섹션을 하단에 추가하거나, 커밋 메시지로 대체.

---

## 10. 리스크와 완화책

| 리스크 | 완화책 |
|---|---|
| 머지 과정에서 예기치 못한 충돌 | worktree를 머지 전까지 보존. 문제 시 `git reset --hard ORIG_HEAD`로 복구 |
| R3(burn 취소) 구현이 ffmpeg 프로세스 제어에서 플랫폼별로 달라짐 | Linux/macOS 컨테이너 환경에서만 검증. `terminate` → `kill` 2단계 전략 |
| R4에서 localStorage 키 변경이 기존 사용자에게 영향 | deprecated 키는 읽기만 하고 쓰지 않음. 값은 무시 |
| 문서 3종 작성이 예상보다 길어짐 | architecture.md를 섹션별 커밋으로 쪼개 진행 |
| 리팩토링 중 회귀 | Phase 3의 각 R 작업은 독립 커밋, 각 커밋 후 `pytest` |

---

## 11. 성공 기준

- [ ] master가 구현물을 포함하는 상태로 정상화됨 (`.worktrees/` 제거)
- [ ] `docs/architecture.md` · `CLAUDE.md` · 새 `README.md` 세 파일이 존재하고 내용 일관성 확보
- [ ] R1~R7 전 이슈 해소, 관련 테스트 추가
- [ ] `uv run pytest` 전 그린
- [ ] `docker compose up`으로 전체 서비스 동작 확인
- [ ] 루트 스크린샷 2장만 `docs/images/`에 남고 나머지 제거

---

## 12. 스펙 이후 과정

이 스펙 승인 후 `superpowers:writing-plans` 스킬로 Phase별 체크리스트 플랜을 작성한다. 플랜은 `docs/superpowers/plans/2026-04-18-stability-refactor/`에 phase 파일로 분할한다.

---

## 13. 변경 이력

- 2026-04-18: 초안 작성 (사용자와 Q1~Q5 합의 후).
