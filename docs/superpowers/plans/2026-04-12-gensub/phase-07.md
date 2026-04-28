# Phase 7 — Backend Docker Smoke Test

이 페이즈에서는 백엔드 단독(프론트엔드 없이)으로 docker compose 스택이 동작하는지 검증한다. 사용자 인터페이스는 아직 없으므로 `curl`로 API를 호출해 end-to-end 동작을 확인한다.

**사전 조건**: Phase 0~6이 모두 완료되고 모든 pytest가 통과한 상태.

---

### Task 7.1: 백엔드 로컬 검증 (도커 없이)

**Files:**
- None (실행만)

- [ ] **Step 1: 백엔드 전체 테스트 실행**

Run: `cd /Users/loki/GenSub/backend && uv run pytest tests/ -v`
Expected: 모든 테스트 통과.

- [ ] **Step 2: API 단독 실행**

Run:
```bash
cd /Users/loki/GenSub/backend
DATABASE_URL="sqlite:///$PWD/../data/db/jobs.db" \
 MEDIA_DIR="$PWD/../data/media" \
 MODEL_CACHE_DIR="$PWD/../data/models" \
 uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
sleep 2
curl -fsS http://localhost:8000/api/health | tee /dev/stderr
kill $API_PID
```

Expected: `{"ok": true, ...}` JSON 응답.

- [ ] **Step 3: 커밋 불필요 (실행 검증만)**

---

### Task 7.2: Docker 이미지 빌드

**Files:**
- None

- [ ] **Step 1: 이미지 빌드**

Run: `docker compose build api`
Expected: 성공적으로 빌드됨. 에러 없이 `gensub:latest` 이미지 생성.

주의: 프론트엔드 빌드 스테이지도 함께 돈다. Phase 0.3에서 만들어둔 최소 SvelteKit 스캐폴드가 있으므로 빌드 성공해야 한다.

- [ ] **Step 2: 빌드 결과 확인**

Run: `docker image ls gensub:latest`
Expected: 이미지가 존재하고 크기는 ~1.5GB 내외 (ffmpeg, mkvtoolnix 포함).

---

### Task 7.3: 전체 스택 기동 + 헬스 체크

**Files:**
- None

- [ ] **Step 1: 데이터 디렉토리 준비**

Run: `cd /Users/loki/GenSub && mkdir -p data/db data/media data/models`

- [ ] **Step 2: `.env` 복사**

Run: `cp .env.example .env`

- [ ] **Step 3: 스택 기동**

Run: `docker compose up -d`

- [ ] **Step 4: 헬스 체크 대기**

Run:
```bash
for i in $(seq 1 15); do
 if curl -fsS http://localhost:8000/api/health > /dev/null; then
 echo "API ready"
 break
 fi
 echo "waiting... $i"
 sleep 2
done
curl -fsS http://localhost:8000/api/health
```
Expected: `{"ok": true, "disk_free": N, "model_cache_size": 0, "role": "api"}`.

- [ ] **Step 5: 워커 로그 확인**

Run: `docker compose logs worker --tail 20`
Expected: `[worker] starting (role=worker, model=small)` 로그가 보임.

- [ ] **Step 6: config 엔드포인트 확인**

Run: `curl -fsS http://localhost:8000/api/config | python3 -m json.tool`
Expected: `default_model`, `available_models`, `max_video_minutes` 등이 포함된 JSON.

---

### Task 7.4: End-to-end 파이프라인 테스트 (짧은 샘플 영상)

**Files:**
- None (수동 E2E)

- [ ] **Step 1: 짧은 YouTube 영상 URL 준비**

공개된 30초~1분 정도의 짧은 영상 URL을 준비한다. 추천: 퍼블릭 도메인 샘플(검색: "youtube test 30s")이나 본인 채널의 테스트 영상. 긴 영상은 첫 테스트로 부적합하다.

- [ ] **Step 2: 작업 생성**

Run:
```bash
JOB_ID=$(curl -fsS -X POST http://localhost:8000/api/jobs \
 -H "Content-Type: application/json" \
 -d '{"url":"<YOUR_SHORT_VIDEO_URL>","model":"tiny"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
echo "job_id=$JOB_ID"
```

Expected: 작업 id가 출력됨. `tiny` 모델은 빠른 검증용 (정확도는 낮지만 수 초 내 전사).

- [ ] **Step 3: 진행률 폴링**

Run:
```bash
while true; do
 STATUS=$(curl -fsS http://localhost:8000/api/jobs/$JOB_ID | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['status'],d['progress'],d.get('stage_message',''))")
 echo "$STATUS"
 case "$STATUS" in
 ready*|failed*) break ;;
 esac
 sleep 2
done
```
Expected: `downloading → transcribing → ready` 순서로 상태가 바뀌고 마지막에 `ready 1.0 준비됐어요`가 출력됨.

- [ ] **Step 4: 자막 파일 확인**

Run: `curl -fsS http://localhost:8000/api/jobs/$JOB_ID/subtitles.srt`
Expected: SRT 형식의 자막이 출력됨 (내용은 영상에 따라 다름).

- [ ] **Step 5: 세그먼트 조회**

Run: `curl -fsS http://localhost:8000/api/jobs/$JOB_ID/segments | python3 -m json.tool | head -30`
Expected: 세그먼트 리스트 JSON.

- [ ] **Step 6: 비디오 Range 스트리밍 확인**

Run:
```bash
curl -sS -D - -o /dev/null -r 0-1023 http://localhost:8000/api/jobs/$JOB_ID/video | head -10
```
Expected: `HTTP/1.1 206 Partial Content`와 `Content-Range: bytes 0-1023/...` 헤더.

- [ ] **Step 7: MKV 먹스 다운로드 테스트**

Run:
```bash
curl -fsS -o /tmp/gensub-test.mkv http://localhost:8000/api/jobs/$JOB_ID/download/video+subs.mkv
file /tmp/gensub-test.mkv
ls -la /tmp/gensub-test.mkv
rm /tmp/gensub-test.mkv
```
Expected: Matroska 포맷 파일이 정상 다운로드됨.

- [ ] **Step 8: 스택 정지**

Run: `cd /Users/loki/GenSub && docker compose down`
Expected: 컨테이너 정상 종료.

- [ ] **Step 9: 검증 결과를 README에 샘플 URL로 기록 (선택)**

필요하면 이번 E2E에 사용한 샘플 영상 URL을 README의 "Testing" 섹션에 남겨두면 이후 회귀 확인이 쉬워진다. 강제는 아님.

---

### Task 7.5: Smoke 검증 완료 표시 커밋

**Files:**
- Modify: `README.md`

- [ ] **Step 1: README에 "스모크 테스트 완료" 배지 또는 노트 추가 (선택)**

Append to `README.md`:

```markdown

## 상태

- [x] 백엔드 파이프라인 smoke test 통과 (Phase 7)
- [ ] 프론트엔드 UI (Phase 8-14)
- [ ] 풀 스택 통합 (Phase 15)
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/loki/GenSub
git add README.md
git commit -m "docs: mark backend smoke test as complete"
```

---
