# Phase 4 — 통합 검증

목표: 리팩토링 전체가 실제로 동작하는지 확인. pytest + docker build + 수동 smoke. 이 단계에서 실패가 나오면 Phase 3의 해당 Task로 돌아가 수정한다.

---

### Task 4.1: 백엔드 전체 테스트

**Files:** (no changes)

- [ ] **Step 1: 클린 상태에서 테스트**

```bash
cd /Users/loki/GenSub/backend
uv run pytest -v 2>&1 | tail -30
```

Expected:
- 전부 pass.
- 테스트 수 ≈ 38 (이전 35 − 1 regenerate 삭제 + 4 신규 [pin, burn_service, backup, burn_cancel]).
- Skip: `test_pipeline_burn_cancel.py` 두 번째 테스트(ffmpeg 실행 필요).

- [ ] **Step 2: 커버리지 빠른 체크**

```bash
uv run pytest --cov=app --cov-report=term-missing 2>&1 | tail -20
```

Expected: 기존 대비 하락 없음. 신규 서비스(`backup.py`, `jobs.py`의 `pin_job`·`request_burn`)는 커버 100% 근접.

- [ ] **Step 3: 타입 체크 (선택)**

```bash
uv run mypy app/ 2>&1 | tail -10 || echo "mypy 미설치/실패 — 무시 가능"
```

테스트가 그린이면 본 단계는 통과.

---

### Task 4.2: 프론트엔드 빌드

**Files:** (no changes)

- [ ] **Step 1: 타입 체크**

```bash
cd /Users/loki/GenSub/frontend
npm run check 2>&1 | tail -15
```

Expected: 에러 0, 경고 최소.

- [ ] **Step 2: 프로덕션 빌드**

```bash
npm run build 2>&1 | tail -15
```

Expected: `frontend/build/index.html` 생성됨. 빌드 에러 없음.

- [ ] **Step 3: 결과 확인**

```bash
ls frontend/build/ | head
```

Expected: `index.html`, `_app/` 등이 보임.

---

### Task 4.3: Docker 이미지 빌드

**Files:** (no changes)

- [ ] **Step 1: 전체 이미지 빌드**

```bash
cd /Users/loki/GenSub
docker compose build 2>&1 | tail -20
```

Expected: 빌드 성공. `procps` 설치 로그가 Stage 2에서 확인됨.

- [ ] **Step 2: 이미지 크기 확인 (참고용)**

```bash
docker images gensub:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

Expected: 대략 1~2GB 범위.

- [ ] **Step 3: 기동 확인**

```bash
docker compose up -d
sleep 5
curl -fsS http://localhost:8000/api/health | head -c 200
echo
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Expected:
- `/api/health` 200 + JSON 응답.
- `gensub-api`, `gensub-worker` 둘 다 `Up`.

- [ ] **Step 4: worker healthcheck 작동 확인**

30초 이상 기다린 후:

```bash
sleep 35
docker inspect gensub-worker --format='{{.State.Health.Status}}'
```

Expected: `healthy`.

- [ ] **Step 5: 컨테이너 중지**

```bash
docker compose down
```

---

### Task 4.4: 수동 Smoke Test

**Files:** (no changes)

전체 파이프라인을 한 번 관통시켜 리팩토링이 실제 동작을 망가뜨리지 않았는지 확인. 짧은 영상(10~30초)이면 충분.

- [ ] **Step 1: 컨테이너 기동 + 브라우저**

```bash
cd /Users/loki/GenSub
docker compose up -d
# 브라우저에서 http://localhost:8000 열기
```

- [ ] **Step 2: 핵심 경로 확인**

다음 순서로 손으로 검증 — 각 단계가 정상 작동해야 다음으로:

1. **Idle**: 짧은 YouTube URL 입력 + `small` 모델 + 한국어 선택 → "자막 만들기" 클릭.
2. **Processing**: 원형 진행률이 움직임. 단계별 카피가 `downloading` → `transcribing`으로 바뀜. ETA 표시.
3. **Ready**: 플레이어 + 세그먼트 리스트 표시. 재생하면 현재 세그먼트 자동 하이라이트.
4. **편집**: 세그먼트 하나를 클릭해 텍스트 수정 → 다른 곳 클릭(blur) → 저장 확인.
5. **다운로드**: `.srt` 칩 클릭 → 파일 다운로드.
6. **Burn**: "다운로드" 버튼 → Bottom Sheet 오픈 → "시작하기" 클릭 → 진행률 다시 움직임.
7. **Burn 취소 (R3 검증!)**: Burn 중에 "취소" 클릭. **10초 내** burning → failed 전이 확인. 로그로 ffmpeg 프로세스 종료 확인:
 ```bash
 docker logs gensub-worker --tail 30
 ```
8. **Burn 재시도**: 새 burn 요청 → 정상 완료 → `burned.mp4` 다운로드.
9. **Sidebar**: 사이드바 열기 → "보관 기간" 영역이 **"N시간 후 자동 삭제"** 텍스트로 표시(선택 UI가 아니라) — R4 검증.
10. **북마크**: 작업 하나를 pin → API 호출 성공, 새로고침 후에도 pinned 유지 — R2 검증.

- [ ] **Step 3: 결과 기록**

각 단계 ✅/❌를 간단히 메모하거나 화면 캡처. 실패 있으면 어느 Task R로 돌아갈지 식별:
- 1~5 실패 → R1 (잘못 지웠을 가능성) 검토
- 6 실패 → R2 (request_burn 서비스) 검토
- 7 실패 → R3 (burn 취소) 검토
- 9 실패 → R4 (sidebar ttl) 검토

- [ ] **Step 4: 정리**

```bash
docker compose down
# 테스트 중 만들어진 작업이 있으면 필요 시 volume 비우기:
# docker volume rm gensub-data # ⚠️ 데이터 전부 삭제
```

---

### Phase 4 완료 조건

- [ ] `uv run pytest` 전 그린 (≈38개)
- [ ] `npm run check` / `npm run build` 에러 없음
- [ ] `docker compose build` 성공
- [ ] `docker compose up` 후 `/api/health` 200
- [ ] worker healthcheck `healthy`
- [ ] 수동 smoke 10단계 전부 ✅
- [ ] 특히 **R3 burn 취소**가 체감 가능하게(10초 내) 작동

전부 통과하면 Phase 5 진행.
