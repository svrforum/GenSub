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
- 구현 플랜: `docs/superpowers/plans/2026-04-12-gensub/README.md`

## 상태

- [x] 백엔드 pytest 전체 통과 (76 tests, Phase 1–6)
- [x] 백엔드 로컬 smoke 검증 (`uvicorn --factory app.main:create_app` + `/api/health`, `/api/config`)
- [ ] Docker smoke test (Phase 7.2–7.4) — `docker compose up` 필요
- [ ] 프론트엔드 UI (Phase 8–14)
- [ ] 풀 스택 E2E (Phase 15)
