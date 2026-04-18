> ℹ️ **이 문서는 2026-04-11 시점의 초기 설계 명세**입니다. 설계 의도(왜 이렇게 만들었나)를 보존하기 위해 유지되지만, **현재 구현된 아키텍처는 [`docs/architecture.md`](../../architecture.md)를 참고**하세요. 2026-04-18의 안정성 리팩토링 스펙은 [`2026-04-18-stability-refactor-design.md`](2026-04-18-stability-refactor-design.md)에 있습니다.

---

# GenSub 설계 명세서

**날짜**: 2026-04-11
**프로젝트**: GenSub — YouTube 영상용 자막 생성·편집·스트리밍 웹 서비스
**스코프**: 개인용 ~ 소규모 팀 공유 서비스 (동시 사용자 수 명 내외)

---

## 1. 개요

GenSub은 YouTube 영상 URL(또는 업로드된 로컬 영상 파일)을 입력받아 **로컬에서 Whisper 기반 음성 인식으로 자막을 생성**하고, 생성된 자막을 **브라우저에서 영상과 함께 시청·편집·다운로드**할 수 있게 해주는 자체 호스팅 웹 서비스다.

핵심 가치:
- **로컬 우선**: 기본 동작은 외부 API 의존 없이 로컬에서 완결. 프라이버시 보존, 비용 0.
- **원커맨드 실행**: `docker compose up` 한 번으로 M4 Mac과 Intel/AMD Linux 모두에서 동일하게 동작.
- **실용적 편집기**: Whisper의 오인식을 브라우저에서 바로 고칠 수 있는 최소한의 편집 UX.
- **Toss × Apple 디자인 언어**: 미니멀, 친근한 한국어 마이크로카피, 스프링 애니메이션, 글래스모피즘.

---

## 2. 범위 (Goals / Non-Goals)

### Goals
- 사용자 인증 없는 stateless 일회성 작업 처리
- YouTube URL 및 yt-dlp 지원 다른 사이트(일부)로부터 영상 가져오기
- 로컬 영상 파일 드래그 앤 드롭 업로드
- `faster-whisper`를 기본 엔진으로 사용한 음성 인식 (원어 전사)
- 자동 언어 감지 + 수동 지정 (Whisper 지원 전체 언어)
- 웹 브라우저 내 영상 스트리밍 + VTT 소프트 자막 재생
- 세그먼트 단위 텍스트/타임스탬프 편집, 특정 구간만 재전사
- 여러 포맷으로 자막 다운로드 (SRT, VTT, TXT, JSON, mkv 먹스)
- 옵션: ffmpeg로 자막을 영상에 구운(burned-in) mp4 다운로드
- 일정 시간 이후 작업 파일 자동 정리
- `WORKER_CONCURRENCY` env로 동시 작업 수 조절 가능 (기본 1, 권장 상한 4)
- OpenAI Whisper API를 선택적 백엔드로 지원

### Non-Goals
- 사용자 인증, 계정 시스템, 팀 권한 관리 — **스코프 외 (stateless 채택)**
- 번역, 이중 자막, 언어 학습 기능 — **시나리오 B로 스코프 한정**
- 화자 분리, 음원 분리 같은 고급 오디오 처리 — 1차 범위 외
- 대규모 동시 처리, 자동 스케일링, 수평 확장 — 소규모 팀 이하 스코프에 불필요
- 모바일 네이티브 앱, 반응형 디자인은 데스크톱 우선

---

## 3. 아키텍처

### 3.1 컨테이너 토폴로지

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose                        │
│                                                             │
│   ┌──────────────────────┐      ┌─────────────────────┐    │
│   │   api (FastAPI)      │      │   worker (Python)   │    │
│   │                      │      │                     │    │
│   │  • REST + SSE        │      │  • Job 폴링 루프    │    │
│   │  • SvelteKit 정적    │      │  • yt-dlp           │    │
│   │    파일 서빙         │      │  • faster-whisper   │    │
│   │  • 파일 스트리밍     │      │  • ffmpeg 렌더링    │    │
│   │    (HTTP Range)      │      │                     │    │
│   └──────────┬───────────┘      └──────────┬──────────┘    │
│              │                              │              │
│              └──────┬───────────────┬───────┘              │
│                     ▼               ▼                      │
│              ┌─────────────┐  ┌─────────────────┐          │
│              │ ./data/db   │  │  ./data/media   │          │
│              │  jobs.db    │  │  (공유 볼륨)    │          │
│              │ (SQLite)    │  │                 │          │
│              └─────────────┘  └─────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ :8000 (호스트 포트)
                          ▼
                     브라우저
```

### 3.2 핵심 아키텍처 결정

| # | 결정 | 근거 |
|---|---|---|
| 1 | API와 Worker를 별도 컨테이너로 분리 | Whisper 크래시/OOM이 웹 UI를 죽이지 않게 격리 |
| 2 | 동일 Docker 이미지로 두 역할 실행 (`GENSUB_ROLE` env로 분기) | 빌드·배포 단순화, 서비스 레이어 코드 공유 |
| 3 | 메시지 브로커(Redis 등) 없이 SQLite로 작업 큐 구현 | A/B 스코프에 Redis는 오버킬. 단일 파일 DB로 충분 |
| 4 | SQLite는 WAL 모드로 열어 동시 읽기/쓰기 경합 완화 | 폴링 주기(1~2초) 수준의 동시성에는 충분 |
| 5 | 진행률 전달은 SSE (Server-Sent Events) | 단방향 스트림에 WebSocket보다 단순, HTTP 프록시 통과 쉬움 |
| 6 | 영상 스트리밍은 FastAPI FileResponse + HTTP Range | 재인코딩 없이 원본 mp4를 `<video>` 태그로 직접 재생 |
| 7 | 프론트엔드는 SvelteKit 정적 빌드를 FastAPI가 서빙 | 단일 프로세스로 프론트까지 커버, 별도 Nginx 불필요 |
| 8 | 볼륨은 bind mount (`./data`) | 사용자가 파일을 직접 열람·백업 가능 (Toss적 투명성) |
| 9 | Whisper 모델 캐시를 별도 볼륨 (`./data/models`) | 컨테이너 재빌드 시 수 GB 재다운로드 방지 |
| 10 | 기본 STT 엔진은 `faster-whisper`, OpenAI API는 옵션 폴백 | Mac/Linux 양쪽에서 동일 API, CPU int8로 M4에서 충분히 빠름 |

### 3.3 데이터 흐름

```
[브라우저]
    │
    │ 1. POST /api/jobs { url, model, language }
    ▼
[FastAPI API]
    │
    │ 2. SQLite에 Job 레코드 생성 (status=pending)
    │    응답: { job_id }
    ▼
[SQLite jobs.db]  ◀─────────── 3. 폴링 (1~2s)
    ▲                         │
    │                         │
    │ 4. 상태/진행률 업데이트 │
    │                         ▼
    │                    [Python Worker]
    │                         │
    │                         │ 5. yt-dlp 다운로드 → source.mp4
    │                         │ 6. ffmpeg로 wav 추출
    │                         │ 7. faster-whisper 전사
    │                         │ 8. SRT/VTT 생성
    │                         │ 9. status=ready, 세그먼트 DB 저장
    │                         ▼
    │                    [./data/media/<job_id>/]
    │                         source.mp4
    │                         audio.wav
    │                         subtitles.srt
    │                         subtitles.vtt
    │
    │ 10. SSE로 브라우저에 진행률 push
    ▼
[브라우저]
    │
    │ 11. status=ready 수신 → 플레이어 + 편집기 표시
    │ 12. GET /api/jobs/:id/video (HTTP Range 스트리밍)
    │ 13. GET /api/jobs/:id/subtitles.vtt (<track>)
```

---

## 4. 처리 파이프라인과 작업 상태

### 4.1 작업 상태 머신

```
pending → downloading → transcribing → ready
                                         │
                       (사용자가 "구워서 다운로드" 클릭 시)
                                         ▼
                                      burning → done
       ┌────────────────────────────────┘
       ▼
   failed (어느 단계에서든 실패 시, 에러 메시지 포함)
```

상태 정의:

| 상태 | 의미 | 사용자가 할 수 있는 것 |
|---|---|---|
| `pending` | 작업 생성됨, 워커가 아직 집지 않음 | 취소 |
| `downloading` | yt-dlp로 영상 다운로드 중 | 취소, 진행률 관찰 |
| `transcribing` | Whisper 전사 중 | 취소, 진행률 관찰 |
| `ready` | 전사 완료, VTT 자막 생성됨 | 시청, 편집, 재전사, 다운로드, 구워서 다운로드 요청 |
| `burning` | ffmpeg로 자막 굽는 중 | 진행률 관찰 (취소 가능) |
| `done` | burn-in 완료 | 구워진 mp4 다운로드 |
| `failed` | 어느 단계든 실패 | 에러 확인, 재시도 |

**핵심 설계**: `ready`에 도달하면 대부분의 사용 목적(시청, 편집, SRT 다운로드)이 충족된다. `burning`은 **사용자가 명시적으로 요청할 때만** 시작되는 옵션 파이프라인이다.

### 4.2 단계별 상세

**1단계: 다운로드 (yt-dlp)**
- `yt-dlp`를 파이썬 라이브러리로 직접 호출 (서브프로세스 X)
- 포맷 선택자: `bv*+ba/b` — 최적 비디오+오디오 병합
- 출력: `./data/media/<job_id>/source.mp4`
- 진행률 훅(`progress_hooks`)을 DB에 초당 1회 throttle하여 기록
- 쿠키/지역 제한 영상 대응을 위한 `cookies.txt` 경로를 env로 받음 (선택)
- 로컬 파일 업로드 경로: yt-dlp를 우회하고 업로드된 파일을 `source.*`로 저장한 뒤 바로 2단계 진입

**2단계: 음성 추출 및 전사 (faster-whisper)**
- ffmpeg로 `source.mp4` → 16kHz 모노 wav 추출 (`audio.wav`)
- `faster-whisper`의 `transcribe()` 호출
  - `beam_size=5`
  - `vad_filter=True` — 무음 구간 자동 컷
  - `word_timestamps=True` — 단어 단위 타임스탬프 (편집기 유용)
  - 언어는 자동 감지 또는 사용자 지정
  - 기본 모델: `small`. 사용자가 `tiny`/`base`/`small`/`medium`/`large-v3` 중 선택
  - 연산 정밀도: `COMPUTE_TYPE` env에 따라 `int8` (CPU) 또는 `float16` (GPU)
  - `initial_prompt`: 사용자 사전 기능으로 전달 가능 (2차 기능)
- 결과를 `Segment` 레코드로 DB에 저장 + `subtitles.srt`, `subtitles.vtt` 파일 생성
- 진행률 계산: 처리된 타임스탬프 / 총 오디오 길이

**3단계: Ready 상태**
- 영상은 HTTP Range로 스트리밍, 자막은 VTT를 `<track>`로 로드
- 세그먼트 편집은 DB 업데이트 + SRT/VTT 재생성으로 즉시 반영
- 다운로드 옵션:
  - `subtitles.srt` / `subtitles.vtt` 단독
  - `transcript.txt` (순수 텍스트)
  - `transcript.json` (타임스탬프 포함)
  - `video+subs.mkv` (mkvmerge로 먹스, 재인코딩 없음, 수 초 소요)

**4단계: Burn-in (옵션)**
- 사용자가 "영상에 구워서 다운로드" 클릭 시 트리거
- SRT를 ASS로 변환 (폰트/크기/외곽선 스타일 반영)
- ffmpeg 명령: `ffmpeg -i source.mp4 -vf "subtitles=subtitles.ass" -c:a copy output.mp4`
- 영상 길이의 0.3~1배 시간 소요 (무거움)
- 완료 후 `burned.mp4`를 다운로드 가능

### 4.3 에러 처리 전략

| 시나리오 | 처리 |
|---|---|
| yt-dlp 실패 (삭제/지역/나이 제한) | 에러 메시지 원문 그대로 사용자에게 노출, 재시도 버튼 |
| 영상이 `MAX_VIDEO_MINUTES` 초과 | 작업 생성 단계에서 거부 (기본 90분) |
| Whisper OOM | 한 단계 낮은 모델로 자동 폴백, 경고 메시지 |
| 디스크 부족 | 작업 시작 전 `shutil.disk_usage` 확인, 부족 시 거부 |
| 워커 크래시 | API 시작 시 진행 중 상태인 작업을 `failed`로 마킹 (좀비 정리) |
| 사용자 취소 | `cancel_requested=True`. 워커가 주기적으로 확인해 즉시 중단 + 파일 정리 |
| SSE 연결 끊김 | 클라이언트 자동 재연결 (3회까지), 실패 시 수동 새로고침 유도 |

---

## 5. 기능 세트

### 5.1 MVP (1차 릴리스)

**필수 기능**
1. YouTube URL 입력 폼
2. Whisper 모델 선택 (`tiny`/`base`/`small`/`medium`/`large-v3`, 기본 `small`)
3. 언어 자동 감지 또는 수동 지정
4. SSE 기반 실시간 진행률 표시
5. 브라우저 내 영상 시청 (Plyr 또는 커스텀 플레이어 + VTT)
6. 세그먼트 편집기: 텍스트 수정, `±0.1초` 타이밍 조정
7. 특정 세그먼트 재전사 ("이 구간만 다시")
8. 다운로드: SRT, VTT, TXT, JSON, mkv 먹스
9. burn-in 다운로드 (자막 구운 mp4)
10. 작업 파일 자동 정리 (기본 24h)
11. 에러 표시 + 재시도
12. 저신뢰도 하이라이트 (`avg_logprob` 기반)
13. 키보드 단축키 (Space/↑↓/Enter/Esc/⌘F/R/J/L)
14. 클릭 투 점프 (세그먼트 클릭 → 영상 해당 시점)
15. 찾아 바꾸기 (전체 자막 일괄 교체)
16. 로컬 파일 드래그 앤 드롭 업로드
17. 남은 시간 ETA 계산 및 표시
18. 작업 취소 버튼
19. 다크/라이트 모드 (시스템 자동 감지 + 수동 토글)
20. 한국어 UI

### 5.2 2차 확장 기능 (명세에 포함, 구현은 별도 플랜)

- 사용자 사전 / 초기 프롬프트 입력 (Whisper `initial_prompt`)
- 자막 스타일 프리셋 (폰트, 크기, 외곽선) — burn-in 반영
- 여러 URL 배치 처리
- YouTube 외 yt-dlp 지원 사이트 검증 테스트

### 5.3 3차 (Future Work, 구현 계획 밖)

- 화자 분리 (pyannote.audio)
- 음원 분리 (Demucs)
- 번역 / 이중 자막
- ASS / LRC 포맷 내보내기
- whisper.cpp (Metal 가속) 백엔드

---

## 6. API 및 데이터 모델

### 6.1 SQLite 스키마

```python
class Job(SQLModel, table=True):
    id: str = Field(primary_key=True)                # UUID4
    source_url: str | None                            # YouTube 등 URL (업로드면 None)
    source_kind: str                                  # "url" | "upload"
    title: str | None                                 # yt-dlp 메타데이터에서
    duration_sec: float | None
    language: str | None                              # 자동 감지 결과 or 지정
    model_name: str
    initial_prompt: str | None                        # 2차 기능
    status: str
    progress: float                                   # 0.0 ~ 1.0 (현재 단계)
    stage_message: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    cancel_requested: bool = False

class Segment(SQLModel, table=True):
    id: int = Field(primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    idx: int
    start: float                                      # 초
    end: float
    text: str
    avg_logprob: float | None                         # 저신뢰도 판별용
    no_speech_prob: float | None
    edited: bool = False
    words: str | None                                 # JSON: word-level timestamps
```

- 데이터베이스 파일: `./data/db/jobs.db`
- `PRAGMA journal_mode=WAL` 활성화

### 6.2 REST API 엔드포인트

**작업 생성 및 관리**
```
POST   /api/jobs
         body: { url?, model, language?, initial_prompt? }
         → { job_id, status: "pending" }

POST   /api/jobs/upload
         multipart: file + { model, language?, initial_prompt? }
         → { job_id }

GET    /api/jobs/{id}
         → Job JSON

GET    /api/jobs/{id}/events                    # SSE 스트림
         event 형식: { status, progress, stage_message, eta_sec? }

POST   /api/jobs/{id}/cancel
         → { ok: true }

DELETE /api/jobs/{id}                           # 즉시 삭제
```

**미디어**
```
GET    /api/jobs/{id}/video                     # HTTP Range 스트리밍
GET    /api/jobs/{id}/subtitles.vtt
GET    /api/jobs/{id}/subtitles.srt
GET    /api/jobs/{id}/transcript.txt
GET    /api/jobs/{id}/transcript.json
GET    /api/jobs/{id}/download/video+subs.mkv
POST   /api/jobs/{id}/burn
GET    /api/jobs/{id}/download/burned.mp4
```

**세그먼트 편집**
```
GET    /api/jobs/{id}/segments
PATCH  /api/jobs/{id}/segments/{idx}
         body: { text?, start?, end? }
POST   /api/jobs/{id}/segments/{idx}/regenerate
POST   /api/jobs/{id}/search_replace
         body: { find, replace, case_sensitive? }
         → { changed_count }
```

**기타**
```
GET    /api/health                              # { ok, model_cache_size, disk_free }
GET    /api/config                              # 프론트용 기본값, 모델 목록, 제한값
```

### 6.3 SSE 이벤트 포맷

```
event: progress
data: {"status":"transcribing","progress":0.42,"stage_message":"음성을 듣고 있어요","eta_sec":180}

event: segment_ready
data: {"idx":12,"start":45.2,"end":48.7,"text":"..."}

event: done
data: {"status":"ready"}

event: error
data: {"message":"..."}
```

### 6.4 세그먼트 재전사 동작

"이 구간만 다시" 동작:
1. 해당 세그먼트의 `start`~`end` 범위(+앞뒤 2초 패딩)로 `audio.wav` 슬라이싱
2. Whisper를 해당 조각에만 실행
3. 결과로 나온 세그먼트(들)로 원본을 교체 (1개 → 여러 개 또는 반대도 허용)
4. DB + SRT/VTT 즉시 재생성
5. 클라이언트가 세그먼트 리스트를 다시 불러와 UI 반영

---

## 7. 프론트엔드 UX 및 디자인 언어

### 7.1 디자인 철학 — Toss × Apple

두 디자인 언어의 공통 뿌리: **미니멀리즘, 타이포그래피 중심, 넉넉한 여백, 품질 높은 스프링 애니메이션, 시스템 일관성**.

| 축 | Toss | Apple | GenSub 적용 |
|---|---|---|---|
| 초점 | 한 화면 = 한 가지 일 | 명료성·깊이·겸손 | 상태에 따라 중심이 이동하는 단일 SPA |
| 타이포 | 크고 굵은 제목, 친근한 카피 | SF Pro, Dynamic Type | Pretendard Variable + SF Pro fallback |
| 컬러 | Toss Blue CTA, 선명한 대비 | 시스템 그레이, vibrancy | Toss Blue `#3182F6`를 유일한 primary |
| 움직임 | 스프링, 부드러운 전환 | 스프링, 물리 기반 | Svelte Motion 스프링 (stiffness 260, damping 30) |
| 마이크로카피 | 친근한 한국어 | 간결 | 구어체 한국어: "준비됐어요", "이 부분이 조금 자신 없어요" |
| 재료 | 밝은 카드, soft shadow | Vibrancy, backdrop blur | 카드 + 플레이어 컨트롤에 glassmorphism |

### 7.2 디자인 토큰

**타이포그래피**
- Primary: `Pretendard Variable`
- Fallback: `SF Pro Display`, `system-ui`
- Display: 36~48px / 700 / letter-spacing -0.02em
- Title: 22~28px / 700
- Body: 17px / 400
- Caption: 13px / 500
- 숫자: `font-variant-numeric: tabular-nums`

**컬러 — Light**
- Background: `#F9FAFB`
- Surface: `#FFFFFF`
- Text Primary: `#191F28`
- Text Secondary: `#6B7684`
- Divider: `#F2F4F6`
- Primary: `#3182F6`
- Primary Pressed: `#1B64DA`
- Success: `#22C55E`
- Warning: `#F59E0B`
- Danger: `#FF5847`

**컬러 — Dark**
- Background: `#000000`
- Surface: `#1C1C1E`
- Surface Elevated: `#2C2C2E`
- Text Primary: `#FFFFFF`
- Text Secondary: `#98989F`
- Primary: `#4C9AFF`

**모양**
- Radius: 카드 20px, 버튼 14px, 입력 12px, 배지 8px
- Shadow (light): `0 1px 2px rgba(20,20,43,0.04), 0 12px 40px rgba(20,20,43,0.06)`
- Shadow (dark): 없음, 대신 `border: 1px solid rgba(255,255,255,0.06)`

**간격**: 4의 배수 (4, 8, 12, 16, 20, 24, 32, 48, 64)

**애니메이션**
- Svelte spring (카드 전환): `{ stiffness: 0.15, damping: 0.8 }`
- Svelte spring (버튼): `{ stiffness: 0.25, damping: 0.6 }`
- 페이지 전환: crossfade + 8px translateY
- 버튼 press: `scale(0.97)`, 80ms
- 숫자 카운터: crossfade + 미세 blur
- 모든 전환은 200~400ms, CSS linear 금지

**아이콘**: `lucide-svelte`, stroke 1.75

### 7.3 화면 흐름 — 하나의 페이지, 중심 이동

GenSub은 상태에 따라 주연이 바뀌는 단일 SPA이다.

**Step 1: Idle — "영상 주소를 알려주세요"**
- 페이지 중앙에 단 하나의 큰 입력 필드
- 하단 라인 스타일 입력, 포커스 시 Toss Blue
- 모델/언어는 인라인 선택 (iOS segmented control 스타일)
- "자막 만들기" 풀너비 primary CTA (높이 56px, radius 14px)
- 드래그 영역은 점선 박스 없이 텍스트만, 드래그 시작 시 전체 화면이 반응

**Step 2: Processing — "잠시만 기다려 주세요"**
- 입력 카드가 위로 축소 소멸 (스프링)
- 중앙에 썸네일 + 제목 카드
- 큰 원형 진행률 (지름 140px, 선 8px, Toss Blue, round cap)
- 진행률 숫자는 Display 사이즈, crossfade 트랜지션
- 단계별 카피 로테이션:
  - `pending` → "준비하고 있어요"
  - `downloading` → "영상을 가져오고 있어요"
  - `transcribing` → "음성을 듣고 있어요"
  - `burning` → "자막을 영상에 입히고 있어요"
- 같은 단계에서 10초마다 카피 바뀜 (정지감 방지)
- 남은 시간 ETA 표시
- 텍스트 "취소" 버튼

**Step 3: Ready — "준비됐어요"**
- 진행률 카드가 위로 접히며 사라짐
- 플레이어 + 편집기가 아래에서 올라옴 (spring)
- 좌: 커스텀 비디오 플레이어 (glassmorphism 컨트롤, `backdrop-filter: blur(20px)`)
- 우: 세그먼트 리스트 (카드 스타일, hover 미세 강조)
- 현재 재생 중 세그먼트: 왼쪽 4px Toss Blue 바 + `scale(1.02)`
- 저신뢰도 세그먼트: 연노랑 배경 (`#F59E0B` 10% opacity)
- 텍스트 클릭 = 인플레이스 편집 (contentEditable)
- 상단 찾아 바꾸기 패널 (`⌘F`로 토글)
- 하단 다운로드 칩: `[.srt] [.vtt] [.txt] [.json] [.mkv]`
- 하단 primary 버튼: `🔥 영상에 구워서 다운로드`

**Step 4: Burn-in — iOS Bottom Sheet**
- 바닥에서 스프링으로 올라오는 모달
- 상단 grab handle
- 폰트/크기/외곽선 옵션 (segmented + switch)
- primary CTA "시작하기", secondary "취소"
- 배경 dim + blur
- 드래그 다운으로 닫기 가능
- "시작하기" 누르면 Step 2 진행률 카드가 다시 등장 (status=`burning`)

### 7.4 상호작용 디테일

**키보드 단축키**

| 키 | 동작 |
|---|---|
| `Space` | 재생/정지 |
| `↑` / `↓` | 이전/다음 세그먼트 |
| `Enter` | 선택 세그먼트 편집 모드 |
| `Esc` | 편집 취소 |
| `⌘/Ctrl + S` | 저장 (자동 저장과 병행) |
| `⌘/Ctrl + F` | 찾아 바꾸기 토글 |
| `R` | 현재 세그먼트 재전사 |
| `J` / `L` | 영상 -5초 / +5초 |

**영상 ↔ 세그먼트 연동**
- 재생 중 현재 시점 세그먼트 자동 하이라이트 + 자동 스크롤
- 세그먼트 클릭 → 영상이 해당 시점으로 점프
- 편집 후 자동 저장 (debounce 500ms)

**세션 복원**
- 작업 생성 시 `{job_id, title, created_at}`을 `localStorage`에 저장
- 탭 닫고 다시 와도 최근 작업을 "📚 최근" 패널에서 클릭 재접속 가능
- 서버가 이미 삭제한 작업은 "만료됨" 표시

**에러 상태**
- 진행률 패널이 danger 컬러로 바뀜
- 친근한 카피 + `▸ 자세히 보기`로 원문 에러 토글
- 재시도 버튼

### 7.5 기술 스택 (프론트엔드)

- **SvelteKit** (adapter-static, SPA 모드)
- **Tailwind CSS** + 커스텀 디자인 토큰
- **Pretendard Variable** (@fontsource-variable/pretendard)
- **lucide-svelte** (아이콘)
- **Plyr** 또는 네이티브 `<video>` + 커스텀 컨트롤
- **svelte/motion** (스프링 기본)

---

## 8. Docker 배포

### 8.1 프로젝트 구조

```
GenSub/
├── compose.yaml
├── compose.override.yaml.example
├── .env.example
├── README.md
├── Dockerfile                      (멀티 스테이지: frontend + python)
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── app/
│   │   ├── main.py                 (FastAPI 엔트리)
│   │   ├── api/                    (라우터)
│   │   ├── core/                   (설정, DB, SSE)
│   │   ├── models/                 (SQLModel)
│   │   └── services/               (파이프라인 로직, 워커와 공유)
│   ├── worker/
│   │   └── main.py                 (워커 엔트리)
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── svelte.config.js            (adapter-static)
│   ├── src/
│   └── static/
├── docs/
│   └── superpowers/specs/
└── data/                           (gitignore, bind mount 대상)
    ├── db/
    ├── media/
    └── models/
```

### 8.2 Dockerfile (멀티 스테이지)

```dockerfile
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
RUN uv sync --frozen --no-dev

COPY backend/ ./

COPY --from=frontend-build /app/build ./app/static

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

멀티 아키텍처 빌드 지원: `docker buildx build --platform linux/amd64,linux/arm64`.

### 8.3 compose.yaml

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
      uv run uvicorn app.main:app
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
      uv run python -m worker.main
    restart: unless-stopped
```

### 8.4 .env.example

```bash
# 호스트에서 접속할 포트
GENSUB_PORT=8000

# 작업 파일 자동 삭제까지의 시간 (시간 단위)
JOB_TTL_HOURS=24

# 처리 가능한 최대 영상 길이 (분)
MAX_VIDEO_MINUTES=90

# 기본 Whisper 모델 (tiny/base/small/medium/large-v3)
DEFAULT_MODEL=small

# 연산 정밀도 (CPU면 int8, NVIDIA GPU면 float16)
COMPUTE_TYPE=int8

# 동시 처리 가능한 작업 수
WORKER_CONCURRENCY=1

# 옵션: OpenAI Whisper API 사용 시
OPENAI_API_KEY=

# CORS (기본 모두 허용)
CORS_ALLOW_ORIGIN=*
```

### 8.5 파일 생명주기 및 정리

- API 시작 시 백그라운드 태스크로 주기적 정리 루프 (1시간 간격)
  - `expires_at < now()` 인 작업 → DB 레코드 삭제 + `data/media/<job_id>/` rmtree
- API 시작 시 좀비 작업 정리: `downloading`/`transcribing`/`burning` 상태를 `failed`로 마킹
- 디스크 용량 확인 후 임계치 이하면 신규 작업 거부

### 8.6 첫 실행 경험

```bash
git clone https://github.com/.../GenSub.git
cd GenSub
cp .env.example .env   # 필요 시 수정
docker compose up -d
open http://localhost:8000
```

README 주의사항:
- 첫 작업 시 Whisper 모델이 `./data/models`에 다운로드됨 (small ≈ 500MB, medium ≈ 1.5GB, large-v3 ≈ 3GB)
- 이미지 빌드에 수 분 소요
- M4 Mac: CPU int8 모드로 충분히 빠름
- Linux + NVIDIA GPU: override 예시대로 `COMPUTE_TYPE=float16` + GPU 자원 할당

### 8.7 개발 모드 (compose.override.yaml.example)

```yaml
services:
  api:
    volumes:
      - ./backend:/app
      - ./data:/data
    command: >
      uv run uvicorn app.main:app
      --host 0.0.0.0 --port 8000
      --reload
  worker:
    volumes:
      - ./backend:/app
      - ./data:/data
    command: >
      uv run watchfiles "python -m worker.main" /app
```

---

## 9. 테스트 전략

- **단위 테스트**: 서비스 레이어 (자막 포맷 변환, 세그먼트 편집, 파일 경로 생성, TTL 계산) — pytest
- **통합 테스트**: SQLite 작업 큐 라이프사이클, SSE 스트림, API 엔드포인트 — pytest + httpx
- **E2E**: 1차에선 수동. README에 짧은 샘플 영상 URL 제공.
- **CI (선택)**: GitHub Actions — lint + unit + 도커 빌드 검증

---

## 10. 보안 및 프라이버시

- 로컬 자체 호스팅 전제 (기본적으로 CORS는 전부 허용, 공개 배포 시 조정 필요)
- 인증 없음 (stateless 스코프 결정사항) — 네트워크 경계에서 접근 제한 필요하면 사용자가 리버스 프록시(nginx, Caddy) 앞단에 배치
- yt-dlp가 가져오는 쿠키 파일은 사용자가 직접 마운트해야만 사용됨
- OpenAI API 키는 env로만 전달, 로그에 출력 금지
- 업로드 파일 크기 제한 env로 설정 가능

---

## 11. Open Questions / Future Work

**구현 단계에서 결정할 사항**
- 영상 파일 스트리밍 시 HTTP 206 Partial Content 처리는 FastAPI의 `FileResponse`로 충분한가, 아니면 직접 구현이 필요한가 (→ 구현 시 측정)
- Plyr 기본 UI를 숨기고 커스텀 오버레이를 쓸지, 처음부터 네이티브 `<video>` + Svelte 커스텀 컴포넌트로 갈지 (→ 디자인 mock 단계에서 결정)
- faster-whisper의 단일 프로세스 내 동시 전사 가능 여부 (기본은 `WORKER_CONCURRENCY=1` 안전 설정)
- burn-in 시 한글 폰트 파일 번들링 방법 (Pretendard TTF를 이미지에 포함할지, 호스트에서 마운트할지)

**2차 이후 고려**
- whisper.cpp(Metal 가속) 백엔드 어댑터
- Redis + ARQ로 큐 교체 (트래픽 증가 시)
- 인증 레이어 (단순 access token → OAuth)
- 공유 링크 (특정 작업을 짧은 토큰 URL로 공유)
- 화자 분리 (pyannote.audio)
- 번역 / 이중 자막

---

## 12. 변경 이력

- 2026-04-11: 초기 설계 작성 (브레인스토밍 세션 결과)
