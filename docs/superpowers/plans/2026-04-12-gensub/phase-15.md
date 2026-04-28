# Phase 15 — Full Stack Integration & E2E

백엔드가 프론트엔드 정적 파일을 서빙하도록 연결하고, 전체 스택이 `docker compose up` 한 번으로 동작하는지 검증한다.

**사전 조건**: Phase 0-14 전체 완료.

---

### Task 15.1: 백엔드가 SvelteKit 빌드 결과를 정적 서빙

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_static_serving.py`

- [ ] **Step 1: 실패 테스트**

Write `backend/tests/test_static_serving.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_root_serves_index_html(tmp_path, monkeypatch):
 monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'st.db'}")
 monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
 monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))

 static_dir = tmp_path / "static"
 static_dir.mkdir()
 (static_dir / "index.html").write_text("<html>stub</html>")
 monkeypatch.setenv("STATIC_DIR", str(static_dir))

 client = TestClient(create_app())
 r = client.get("/")
 assert r.status_code == 200
 assert "stub" in r.text


def test_api_routes_still_work_with_static_mount(tmp_path, monkeypatch):
 monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'st2.db'}")
 monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
 monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
 static_dir = tmp_path / "static"
 static_dir.mkdir()
 (static_dir / "index.html").write_text("<html></html>")
 monkeypatch.setenv("STATIC_DIR", str(static_dir))

 client = TestClient(create_app())
 r = client.get("/api/health")
 assert r.status_code == 200
 assert r.json()["ok"] is True
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_static_serving.py -v`

- [ ] **Step 3: Settings에 static_dir 추가 + 마운트**

Modify `backend/app/core/settings.py`: `Settings` 클래스에 필드 추가:

```python
 static_dir: Path | None = None
```

Modify `backend/app/main.py`: `create_app()` 함수에서 라우터 등록 이후, static_dir이 존재하면 `StaticFiles`로 마운트. 단, `/api/*`와 충돌하지 않도록 루트에서 SPA fallback을 제공.

`create_app()`의 `include_router` 호출 바로 아래에 삽입:

```python
 from pathlib import Path as _Path
 from fastapi.responses import FileResponse
 from fastapi.staticfiles import StaticFiles

 static_dir = settings.static_dir or _Path(__file__).parent / "static"
 if static_dir.exists() and (static_dir / "index.html").exists():
 app.mount(
 "/_app",
 StaticFiles(directory=static_dir / "_app", check_dir=False),
 name="sveltekit-assets",
 )

 @app.get("/{full_path:path}", include_in_schema=False)
 async def spa_fallback(full_path: str):
 if full_path.startswith("api/"):
 from fastapi import HTTPException
 raise HTTPException(status_code=404)
 asset = static_dir / full_path
 if asset.is_file():
 return FileResponse(asset)
 return FileResponse(static_dir / "index.html")
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_static_serving.py -v`
Expected: 2 passed.

Run: `cd backend && uv run pytest tests/ -v`
Expected: 전체 테스트 통과.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/core/settings.py backend/app/main.py backend/tests/test_static_serving.py
git commit -m "feat(backend): serve SvelteKit build as SPA fallback"
```

---

### Task 15.2: 프론트엔드 빌드 결과를 백엔드 이미지에 통합

**Files:**
- 기존 Dockerfile은 Phase 0.4에서 이미 `COPY --from=frontend-build /app/build ./app/static` 를 수행하고 있다. 이 Task에서는 빌드 검증만 한다.

- [ ] **Step 1: 이미지 재빌드**

Run: `docker compose build api`
Expected: 성공. 프론트 빌드 스테이지와 Python 런타임 양쪽 모두 에러 없음.

- [ ] **Step 2: 이미지 내부 확인**

Run:
```bash
docker run --rm gensub:latest ls -la app/static/ | head -10
```
Expected: `index.html`과 `_app` 디렉토리 등 SvelteKit 빌드 결과가 보임.

- [ ] **Step 3: 커밋 불필요 (빌드 검증)**

---

### Task 15.3: 풀 스택 E2E

**Files:**
- None (수동 검증)

- [ ] **Step 1: 스택 기동**

Run: `docker compose up -d && sleep 5`

- [ ] **Step 2: 브라우저 접속**

Run: `open http://localhost:8000`
Expected: GenSub 아이들 화면이 뜬다. Toss 스타일의 "자막 만들 영상 주소를 알려주세요" 타이틀과 큰 입력 필드가 보인다.

- [ ] **Step 3: 짧은 YouTube URL로 실제 처리**

1. 짧은 샘플 영상 URL을 입력.
2. 모델을 `tiny`로, 언어를 `자동 감지`로 설정.
3. "자막 만들기" 클릭.
4. 처리 중 화면으로 전환되어 원형 진행률이 돌아가는지 확인.
5. "영상을 가져오고 있어요" → "음성을 듣고 있어요" 카피 전환 확인.
6. 완료되면 Ready 화면으로 전환.

- [ ] **Step 4: Ready 화면 체크리스트**

- [ ] 비디오 플레이어에서 영상이 재생되고 자막이 표시되는가?
- [ ] 세그먼트 리스트가 우측에 뜨는가?
- [ ] 영상 재생 중 현재 시점 세그먼트가 자동 하이라이트되는가?
- [ ] 세그먼트 시간표시를 클릭하면 영상이 해당 시점으로 점프하는가?
- [ ] 세그먼트 텍스트를 더블클릭하면 편집 가능한가?
- [ ] Enter로 저장, Esc로 취소가 되는가?
- [ ] 저신뢰도 세그먼트가 연노란 배경인가?
- [ ] Space, ↑/↓, J/L 단축키가 동작하는가?
- [ ] `.srt` 다운로드가 동작하는가?
- [ ] `.mkv` 다운로드가 동작하는가?
- [ ] `⌘/Ctrl+F`로 찾아 바꾸기 패널이 열리는가?

- [ ] **Step 5: Burn-in 체크**

1. "🔥 영상에 구워서 다운로드" 클릭
2. Bottom sheet가 아래에서 올라오는가?
3. "시작하기" 클릭 후 처리 화면으로 전환되는가?
4. 완료 후 다운로드 화면이 뜨고 mp4가 받아지는가?

- [ ] **Step 6: 다크 모드 토글**

헤더의 달/해 아이콘으로 다크모드 전환 시 모든 화면의 컬러가 부드럽게 바뀌는지 확인.

- [ ] **Step 7: 스택 정지**

Run: `docker compose down`

---

### Task 15.4: README 최종 업데이트

**Files:**
- Modify: `README.md`

- [ ] **Step 1: README 보강**

Overwrite `README.md`:

```markdown
# GenSub

YouTube 영상 URL이나 로컬 영상 파일을 받아 로컬 Whisper로 자막을 생성하고,
브라우저에서 편집·시청·다운로드할 수 있는 자체 호스팅 웹 서비스.

## 특징

- 🎯 **로컬 우선** — faster-whisper로 외부 API 없이 동작 (OpenAI API는 선택 옵션)
- 🐳 **원커맨드 실행** — `docker compose up -d` 한 번이면 끝
- 🍏 **Toss × Apple 디자인 언어** — 미니멀, 스프링 애니메이션, 다크 모드
- ✍️ **실용적 편집기** — 세그먼트 인플레이스 편집, 구간별 재전사, 찾아 바꾸기
- 📥 **여러 포맷 다운로드** — SRT · VTT · TXT · JSON · MKV · 구운 MP4
- 🔍 **저신뢰도 하이라이트** — Whisper가 자신 없어하는 구간 자동 표시
- ⌨️ **키보드 단축키** — Space, ↑/↓, J/L, ⌘F, R 등

## 빠른 시작

```bash
cp .env.example .env
docker compose up -d
open http://localhost:8000
```

## 요구사항

- Docker 20+, Docker Compose v2+
- 첫 작업 시 Whisper 모델 다운로드 공간 (small ≈ 500MB, large-v3 ≈ 3GB)
- M4 Mac / Intel·AMD Linux 양쪽에서 CPU int8 모드로 동작
- NVIDIA GPU가 있으면 `.env`에서 `COMPUTE_TYPE=float16` 설정

## 환경 변수

`.env.example` 참조. 주요 항목:

| 변수 | 기본값 | 설명 |
|---|---|---|
| `GENSUB_PORT` | 8000 | 호스트 포트 |
| `JOB_TTL_HOURS` | 24 | 작업 파일 자동 삭제 시한 |
| `MAX_VIDEO_MINUTES` | 90 | 최대 영상 길이 |
| `DEFAULT_MODEL` | small | 기본 Whisper 모델 |
| `COMPUTE_TYPE` | int8 | CPU는 int8, GPU는 float16 |
| `WORKER_CONCURRENCY` | 1 | 동시 작업 수 (권장 상한 4) |
| `OPENAI_API_KEY` | (empty) | 옵션: 클라우드 폴백 |

## 개발 모드

```bash
cp compose.override.yaml.example compose.override.yaml
docker compose up
```

백엔드는 `--reload`, 워커는 watchfiles로 자동 재시작.

백엔드 단독 테스트:
```bash
cd backend && uv run pytest tests/ -v
```

프론트엔드 단독 개발:
```bash
cd frontend && npm run dev
```

## 문서

- 설계: `docs/superpowers/specs/2026-04-11-gensub-design.md`
- 구현 플랜: `docs/superpowers/plans/2026-04-12-gensub/README.md`

## 상태

- [x] 백엔드 파이프라인 + API (Phase 0-7)
- [x] 프론트엔드 SPA (Phase 8-14)
- [x] 풀 스택 통합 (Phase 15)
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/loki/GenSub
git add README.md
git commit -m "docs: finalize README with full feature list and status"
```

---

### Task 15.5: 최종 체크 — 전체 테스트 및 빌드

**Files:**
- None

- [ ] **Step 1: 백엔드 전체 테스트**

Run: `cd /Users/loki/GenSub/backend && uv run pytest tests/ -v`
Expected: 모든 테스트 통과.

- [ ] **Step 2: 프론트엔드 체크**

Run: `cd /Users/loki/GenSub/frontend && npm run check && npm run build`
Expected: 타입 체크 통과, 빌드 성공.

- [ ] **Step 3: 도커 이미지 재빌드 검증**

Run: `cd /Users/loki/GenSub && docker compose build --no-cache`
Expected: 성공.

- [ ] **Step 4: E2E 재검증**

Run: `docker compose up -d && sleep 8 && curl -fsS http://localhost:8000/api/health && docker compose down`
Expected: health 응답이 나오고 정상 종료.

- [ ] **Step 5: 최종 커밋 (필요 시)**

```bash
cd /Users/loki/GenSub
git status
# 변경사항 없으면 커밋 불필요
```

---
