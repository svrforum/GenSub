# Conventions

GenSub 프로젝트의 개발 규약. PR/커밋 작성·코드 리뷰 시 따른다.

## 1. 코드 컨벤션

### Python (backend/)

- 버전: Python 3.11+.
- 타입 힌트 필수 (테스트 파일 제외). `from __future__ import annotations` 미사용 (3.11 PEP 604 문법 사용).
- Lint: `ruff` 규칙 `E, F, I, N, UP, B, SIM`. 라인 100자.
- Format: ruff가 포매터 역할도 함. `ruff check --fix .`.
- async: FastAPI 라우터는 `async def` 우선. DB 작업은 SQLAlchemy 동기 세션이므로 `async def` 안에서 blocking 호출도 허용.
- import 순서: stdlib → 3rd party → local. ruff I 규칙이 강제.

### TypeScript / Svelte (frontend/)

- `tsconfig.strict = true`.
- `<script lang="ts">` 기본. JS 파일은 만들지 않음.
- 컴포넌트 파일 **1000줄 초과 시 분리 검토**. 한 책임이라면 1000줄까지는 한 파일이 더 읽기 쉽다.
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

- `screens/` — 상태별 최상위 화면. `current` 스토어의 `screen` 필드로 분기.
- `ui/` — 재사용 컴포넌트. 상태 스토어 import 최소화, props로 받는 것을 우선.
- `api/` — fetch 래핑. 컴포넌트에서 `fetch()` 직접 호출 금지.

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
- `chore/*`: 잡일.

병합은 기본 `--no-ff` (히스토리 보존). Squash는 정말 작은 변경일 때만.

---

## 5. 문서 경로 규칙

| 파일 | 역할 |
|---|---|
| `README.md` | 외부 독자용 소개. |
| `CONVENTIONS.md` | 이 문서. 개발 규약. |
| `docs/architecture.md` | **현재 상태**. 코드와 동기화. 구조 변경 시 같은 PR에서 업데이트. |
| `docs/superpowers/specs/YYYY-MM-DD-*.md` | **변경 제안** (시간 스냅샷). 승인 후 보존, 수정하지 않음. |
| `docs/superpowers/plans/*/` | 실행 플랜 (체크리스트). 진행 중 체크 표시. 완료 후 보존. |

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
