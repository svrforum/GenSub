# GenSub

YouTube 영상 URL이나 로컬 영상 파일을 받아 로컬 Whisper로 자막을 생성하고,
브라우저에서 편집·시청·다운로드할 수 있는 자체 호스팅 웹 서비스.

## 특징

- **로컬 우선** — faster-whisper로 외부 API 없이 동작
- **원커맨드 실행** — `docker compose up -d` 한 번이면 끝
- **Toss x Apple 디자인 언어** — 미니멀, 스프링 애니메이션, 다크 모드
- **실용적 편집기** — 세그먼트 인플레이스 편집, 구간별 재전사, 찾아 바꾸기
- **여러 포맷 다운로드** — SRT / VTT / TXT / JSON / MKV / 구운 MP4
- **저신뢰도 하이라이트** — Whisper가 자신 없어하는 구간 자동 표시
- **키보드 단축키** — Space, Arrow, J/L, Cmd+F, R 등

## 빠른 시작

```bash
cp .env.example .env
docker compose up -d
open http://localhost:8000
```

## 요구사항

- Docker 20+, Docker Compose v2+
- 첫 작업 시 Whisper 모델 다운로드 공간 (small ~ 500MB, large-v3 ~ 3GB)
- M4 Mac / Intel/AMD Linux 양쪽에서 CPU int8 모드로 동작
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

## 개발 모드

```bash
cp compose.override.yaml.example compose.override.yaml
docker compose up
```

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

- [x] 백엔드 파이프라인 + API (Phase 0-7, 78 tests)
- [x] 프론트엔드 SPA (Phase 8-14)
- [x] 풀 스택 통합 코드 (Phase 15)
- [ ] Docker E2E 검증 — `docker compose up` 후 수동 확인 필요
