# Phase 0 — Project Scaffolding

### Task 0.1: 디렉토리 구조와 .gitignore

**Files:**
- Create: `.gitignore`
- Create: `backend/.gitkeep`
- Create: `frontend/.gitkeep`
- Create: `data/.gitkeep`

- [ ] **Step 1: 디렉토리 생성**

```bash
cd /Users/loki/GenSub
mkdir -p backend/app/api backend/app/core backend/app/models backend/app/services backend/worker backend/tests
mkdir -p frontend/src/lib frontend/src/routes frontend/static
mkdir -p data/db data/media data/models
touch backend/.gitkeep frontend/.gitkeep data/.gitkeep
```

- [ ] **Step 2: .gitignore 작성**

Write `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Node
node_modules/
.svelte-kit/
build/
dist/
frontend/package-lock.json
# (keep npm lock by preference — user can uncomment)

# Env
.env
.env.local

# Runtime data (bind mount target)
data/db/*
data/media/*
data/models/*
!data/db/.gitkeep
!data/media/.gitkeep
!data/models/.gitkeep

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
```

- [ ] **Step 3: 커밋**

```bash
git add .gitignore backend/.gitkeep frontend/.gitkeep data/.gitkeep
git commit -m "chore: scaffold project directory layout"
```

---

### Task 0.2: 백엔드 pyproject.toml + uv 초기화

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/README.md`

- [ ] **Step 1: uv 설치 확인**

```bash
uv --version
```

Expected: uv 버전 출력. 없으면 `curl -LsSf https://astral.sh/uv/install.sh | sh`.

- [ ] **Step 2: pyproject.toml 작성**

Write `backend/pyproject.toml`:

```toml
[project]
name = "gensub-backend"
version = "0.1.0"
description = "GenSub backend - FastAPI API + Whisper worker"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "sqlmodel>=0.0.16",
    "pydantic-settings>=2.3",
    "python-multipart>=0.0.9",
    "sse-starlette>=2.1",
    "yt-dlp>=2024.7.1",
    "faster-whisper>=1.0.3",
    "ffmpeg-python>=0.2",
    "httpx>=0.27",
]

[dependency-groups]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.5",
    "mypy>=1.10",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM"]
```

- [ ] **Step 3: uv sync 실행해 lock 파일 생성**

```bash
cd backend
uv sync
```

Expected: `.venv/` 생성되고 `uv.lock`이 생성됨. 에러 없이 완료.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore(backend): initialize uv project with core dependencies"
```

---

### Task 0.3: 프론트엔드 SvelteKit 초기화

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/svelte.config.js`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/app.html`
- Create: `frontend/src/app.css`
- Create: `frontend/src/routes/+layout.svelte`
- Create: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: package.json 작성**

Write `frontend/package.json`:

```json
{
  "name": "gensub-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "vite preview",
    "check": "svelte-check --tsconfig ./tsconfig.json"
  },
  "devDependencies": {
    "@sveltejs/adapter-static": "^3.0.2",
    "@sveltejs/kit": "^2.5.0",
    "@sveltejs/vite-plugin-svelte": "^3.1.0",
    "svelte": "^4.2.0",
    "svelte-check": "^3.8.0",
    "typescript": "^5.5.0",
    "vite": "^5.3.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  },
  "dependencies": {
    "@fontsource-variable/pretendard": "^2.0.0",
    "lucide-svelte": "^0.400.0"
  }
}
```

- [ ] **Step 2: svelte.config.js (adapter-static + SPA fallback)**

Write `frontend/svelte.config.js`:

```javascript
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: 'index.html',
      precompress: false,
      strict: false
    }),
    alias: {
      $lib: 'src/lib'
    }
  }
};
```

- [ ] **Step 3: vite.config.ts + tsconfig.json**

Write `frontend/vite.config.ts`:

```typescript
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
});
```

Write `frontend/tsconfig.json`:

```json
{
  "extends": "./.svelte-kit/tsconfig.json",
  "compilerOptions": {
    "allowJs": true,
    "checkJs": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "sourceMap": true,
    "strict": true,
    "moduleResolution": "bundler"
  }
}
```

- [ ] **Step 4: 기본 앱 껍데기**

Write `frontend/src/app.html`:

```html
<!doctype html>
<html lang="ko" %sveltekit.theme%>
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%sveltekit.assets%/favicon.png" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GenSub</title>
    %sveltekit.head%
  </head>
  <body>
    <div style="display: contents">%sveltekit.body%</div>
  </body>
</html>
```

Write `frontend/src/app.css`:

```css
@import '@fontsource-variable/pretendard';

:root {
  font-family: 'Pretendard Variable', -apple-system, 'SF Pro Display', system-ui, sans-serif;
}
```

Write `frontend/src/routes/+layout.svelte`:

```svelte
<script lang="ts">
  import '../app.css';
</script>

<slot />
```

Write `frontend/src/routes/+page.svelte`:

```svelte
<h1>GenSub</h1>
<p>초기 스캐폴드입니다. Phase 8부터 실제 UI가 붙습니다.</p>
```

- [ ] **Step 5: npm install + 빌드 검증**

```bash
cd frontend
npm install
npm run build
```

Expected: `frontend/build/index.html`이 생성됨.

- [ ] **Step 6: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/
git commit -m "chore(frontend): scaffold SvelteKit with adapter-static"
```

---

### Task 0.4: Dockerfile (멀티 스테이지)

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

- [ ] **Step 1: .dockerignore 작성**

Write `.dockerignore`:

```
**/__pycache__
**/.venv
**/node_modules
**/.svelte-kit
**/build
data/
.git/
.env
.env.local
docs/
```

- [ ] **Step 2: Dockerfile 작성**

Write `Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1.6

# ---- Stage 1: Frontend 빌드 ----
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python 런타임 ----
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        mkvtoolnix \
        libsndfile1 \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ ./

COPY --from=frontend-build /app/build ./app/static

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: 커밋 (아직 빌드는 main.py가 없어서 실패 가능 — 다음 페이즈에서 해결)**

```bash
git add Dockerfile .dockerignore
git commit -m "chore: add multi-stage Dockerfile skeleton"
```

---

### Task 0.5: compose.yaml + .env.example + README

**Files:**
- Create: `compose.yaml`
- Create: `compose.override.yaml.example`
- Create: `.env.example`
- Create: `README.md`

- [ ] **Step 1: compose.yaml 작성**

Write `compose.yaml`:

```yaml
services:
  api:
    build: .
    image: gensub:latest
    container_name: gensub-api
    ports:
      - "${GENSUB_PORT:-8000}:8000"
    environment:
      GENSUB_ROLE: api
      DATABASE_URL: sqlite:////data/db/jobs.db
      MEDIA_DIR: /data/media
      MODEL_CACHE_DIR: /data/models
      JOB_TTL_HOURS: ${JOB_TTL_HOURS:-24}
      MAX_VIDEO_MINUTES: ${MAX_VIDEO_MINUTES:-90}
      DEFAULT_MODEL: ${DEFAULT_MODEL:-small}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      CORS_ALLOW_ORIGIN: ${CORS_ALLOW_ORIGIN:-*}
    volumes:
      - ./data:/data
    command: >
      uv run --no-sync uvicorn app.main:app
      --host 0.0.0.0 --port 8000
      --proxy-headers
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  worker:
    build: .
    image: gensub:latest
    container_name: gensub-worker
    depends_on:
      - api
    environment:
      GENSUB_ROLE: worker
      DATABASE_URL: sqlite:////data/db/jobs.db
      MEDIA_DIR: /data/media
      MODEL_CACHE_DIR: /data/models
      WORKER_CONCURRENCY: ${WORKER_CONCURRENCY:-1}
      DEFAULT_MODEL: ${DEFAULT_MODEL:-small}
      COMPUTE_TYPE: ${COMPUTE_TYPE:-int8}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
    volumes:
      - ./data:/data
    command: >
      uv run --no-sync python -m worker.main
    restart: unless-stopped
```

- [ ] **Step 2: .env.example 작성**

Write `.env.example`:

```bash
GENSUB_PORT=8000
JOB_TTL_HOURS=24
MAX_VIDEO_MINUTES=90
DEFAULT_MODEL=small
COMPUTE_TYPE=int8
WORKER_CONCURRENCY=1
OPENAI_API_KEY=
CORS_ALLOW_ORIGIN=*
```

- [ ] **Step 3: compose.override.yaml.example (개발 모드)**

Write `compose.override.yaml.example`:

```yaml
# 개발용. 이 파일을 compose.override.yaml로 복사해서 사용:
#   cp compose.override.yaml.example compose.override.yaml
services:
  api:
    volumes:
      - ./backend:/app
      - ./data:/data
    command: >
      uv run --no-sync uvicorn app.main:app
      --host 0.0.0.0 --port 8000
      --reload
  worker:
    volumes:
      - ./backend:/app
      - ./data:/data
```

- [ ] **Step 4: README.md 작성**

Write `README.md`:

```markdown
# GenSub

YouTube 영상을 받아 Whisper로 자막을 만들고, 브라우저에서 편집·시청·다운로드할 수 있는 자체 호스팅 웹 서비스.

## 빠른 시작

```bash
cp .env.example .env
docker compose up -d
open http://localhost:8000
```

## 요구사항

- Docker 20+, Docker Compose v2+
- 첫 작업 시 Whisper 모델 다운로드 공간 (small ≈ 500MB, large-v3 ≈ 3GB)

## 개발

```bash
cp compose.override.yaml.example compose.override.yaml
docker compose up
```

## 문서

- 설계: `docs/superpowers/specs/2026-04-11-gensub-design.md`
- 구현 플랜: `docs/superpowers/plans/2026-04-12-gensub.md`
```

- [ ] **Step 5: 커밋**

```bash
git add compose.yaml compose.override.yaml.example .env.example README.md
git commit -m "chore: add docker compose stack and README"
```

---

