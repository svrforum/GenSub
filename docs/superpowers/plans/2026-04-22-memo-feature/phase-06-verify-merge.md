# Phase 6 — 통합 검증 + 문서 + 머지

목표: 전체 테스트, Docker 재빌드, Playwright 수동 smoke, `docs/architecture.md` 업데이트, master 머지.

**전제**: Phase 1~5 완료, pytest 141 passed, 프론트 빌드 OK.

---

### Task 6.1: 기존 데이터 안전성 검증

**Files:** (no changes, 검증만)

**중요**: 사용자 요구 — "현재 데이터가 문제없게 되어야 해요". 이 Task는 기존 Job/Segment 데이터가 새 테이블 추가 후에도 정상 조회되는지 확인.

- [ ] **Step 1: 현재 Docker 상태 체크 + 데이터 스냅샷**

```bash
cd /Users/loki/GenSub
docker ps --format "table {{.Names}}\t{{.Status}}" 2>&1
docker volume ls | grep gensub 2>&1
```

Expected: `gensub-api`, `gensub-worker` 이미 running이거나 stopped. volume `gensub_gensub-data` 존재.

기존 Job들 목록 기록 (변경 후 비교용):
```bash
docker compose up -d api 2>&1 | tail -3
sleep 3
curl -sS http://localhost:8000/api/jobs?limit=100 | python3 -m json.tool > /tmp/jobs-before.json
wc -l /tmp/jobs-before.json
docker compose down 2>&1 | tail -3
```

- [ ] **Step 2: 신규 이미지 빌드**

```bash
docker compose build 2>&1 | tail -8
```

Expected: 빌드 성공. procps, ffmpeg 등 apt 설치 로그 확인.

- [ ] **Step 3: 신규 이미지로 기동 후 DB 백업 확인**

```bash
docker compose up -d 2>&1 | tail -5
sleep 5
docker exec gensub-api ls -la /data/db/backups/ | tail -5
```

Expected: 새 백업 파일이 timestamp와 함께 생성됨 (R6의 자동 백업).

- [ ] **Step 4: 기존 데이터 접근 확인**

```bash
curl -sS http://localhost:8000/api/jobs?limit=100 | python3 -m json.tool > /tmp/jobs-after.json
diff /tmp/jobs-before.json /tmp/jobs-after.json && echo "IDENTICAL" || echo "DIFFERENCES ABOVE"
```

Expected: 데이터 동일. 차이가 있으면 디버그.

- [ ] **Step 5: 새 테이블 생성 확인**

```bash
docker exec gensub-api python3 -c "
import sqlite3
conn = sqlite3.connect('/data/db/jobs.db')
cur = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\")
for row in cur.fetchall():
 print(row[0])
"
```

Expected: `job`, `memo`, `segment` 세 테이블. `memo` 가 새로 생성됨.

- [ ] **Step 6: memo 테이블이 비어있는지 확인**

```bash
docker exec gensub-api python3 -c "
import sqlite3
conn = sqlite3.connect('/data/db/jobs.db')
n = conn.execute('SELECT COUNT(*) FROM memo').fetchone()[0]
print(f'memo rows: {n}')
"
```

Expected: `memo rows: 0` (방금 생성됨).

- [ ] **Step 7: 정리**

```bash
docker compose down 2>&1 | tail -3
```

---

### Task 6.2: 백엔드 테스트 + 프론트 빌드

**Files:** (no changes)

- [ ] **Step 1: 백엔드 전체 pytest**

```bash
cd /Users/loki/GenSub/backend
uv run pytest -v 2>&1 | tail -20
```

Expected: 141 passed (95 baseline + 5 model + 6 toggle + 8 CRUD + 7 global + 4 schemas + 6 POST + 5 list + 4 delete + 2 cascade = 142... 다를 수 있음, 중요한 건 **전부 pass**).

- [ ] **Step 2: 프론트 체크 + 빌드**

```bash
cd ../frontend
npx svelte-kit sync 2>&1 | tail -3
npm run check 2>&1 | tail -5
npm run build 2>&1 | tail -5
```

Expected: 0 errors, 빌드 성공.

- [ ] **Step 3: ruff 검사**

```bash
cd ../backend
uv run ruff check app/ tests/ 2>&1 | tail -5
```

Expected: 통과 또는 pre-existing warnings only.

---

### Task 6.3: Playwright UI smoke

**Files:** (no changes)

- [ ] **Step 1: Docker 재기동**

```bash
cd /Users/loki/GenSub
docker compose up -d 2>&1 | tail -5
# 헬스체크 대기
until curl -fsS http://localhost:8000/api/health > /dev/null 2>&1; do sleep 1; done
echo "ready"
```

- [ ] **Step 2: 브라우저로 UI smoke — 수동 / Playwright MCP**

브라우저 http://localhost:8000 접속. 다음 단계 확인:

1. 사이드바에 **"영상 2 / 메모 0"** (또는 실제 카운트) 탭이 보이고, 기본으로 **영상** 탭 선택
2. 기존 작업(`059ddd86…` "Why movies these days SUCK") 이 영상 탭에 북마크 아이콘으로 표시 (Phase 이전 동일)
3. 기존 작업 클릭 → ReadyScreen 정상 로드 (플레이어 + 자막 + 782 세그먼트)
4. 첫 번째 세그먼트 우측에 **📎 아이콘** 존재 (outline)
5. 📎 클릭 → 파랑 fill + 아래에 "＋ 메모 추가" 링크 표시
6. "＋ 메모 추가" 클릭 → textarea 나타남 → "테스트 메모" 입력 → Enter → 저장됨, "💭 테스트 메모" 표시
7. 사이드바 **메모 탭** 클릭 → 방금 저장한 메모 카드 표시: 자막 텍스트 + "💭 테스트 메모" + 영상 제목 + 타임스탬프
8. 메모 카드 클릭 → 같은 ReadyScreen 유지 + 해당 세그먼트 시점으로 seek (영상이 해당 위치에서 재생 시작)
9. 📎 재클릭 (메모 내용 있음) → confirm 다이얼로그 → 확인 → 메모 삭제 → 사이드바 메모 탭 비워짐
10. 다른 세그먼트 📎 → 내용 없이 저장 → 📎 재클릭 → 바로 삭제 (confirm 없이)
11. 작업 이력 삭제 (영상 탭에서 기존 작업 hover → 삭제) → 다이얼로그에 "메모 N개도 함께 삭제" 문구 확인 (메모가 있을 때만)

- [ ] **Step 3: Playwright MCP 사용 시 스크린샷 저장 (옵션)**

브라우저가 MCP 세션이면 다음 스크린샷 남기기:
- `docs/images/test-memo-01-empty-tab.png`: 사이드바 메모 탭 빈 상태
- `docs/images/test-memo-02-segment-bookmark.png`: 📎 버튼 저장됨 상태
- `docs/images/test-memo-03-memo-list.png`: 메모 탭에 카드 리스트
- `docs/images/test-memo-04-open-at-time.png`: 메모 클릭 후 해당 시점 재생

(또는 이 Task는 skip하고 수동 확인만)

- [ ] **Step 4: 정리 (선택)**

```bash
docker compose down 2>&1 | tail -3
```

---

### Task 6.4: `docs/architecture.md` 업데이트

**Files:**
- Modify: `docs/architecture.md`

스펙 §5.5 "확장 지점"·§4 "기능 카탈로그"에 메모 항목 추가.

- [ ] **Step 1: 현재 architecture.md 에서 기능 카탈로그 섹션 찾기**

```bash
grep -n "^## 4\|기능 카탈로그" docs/architecture.md
```

- [ ] **Step 2: 기능 카탈로그 표에 메모 행 추가**

Edit `docs/architecture.md`. §4 표의 마지막 행(키보드 단축키 아래 쯤)에 다음 행들 추가:

```markdown
| 세그먼트 메모 저장/해제 | `SegmentMemo.svelte` | `POST /api/jobs/<id>/segments/<idx>/memo` | `services/memo.toggle_save_memo` |
| 메모 텍스트 수정 | `SegmentMemo.svelte` | `PATCH /api/memos/<id>` | `services/memo.update_memo_text` |
| 전역 메모 리스트 | `Sidebar.svelte` 메모 탭 + `MemoCard.svelte` | `GET /api/memos` | `services/memo.list_all_memos_with_liveness` |
| Job별 메모 조회 | `jobMemos` store (SegmentList 상태용) | `GET /api/jobs/<id>/memos` | `services/memo.list_memos_for_job` |
| 메모 삭제 | `MemoCard.svelte` 삭제 버튼 | `DELETE /api/memos/<id>` | `services/memo.delete_memo` |
| 보러가기 (메모→영상) | `openMemo` + `ReadyScreen.svelte` reactive seek | - | - (프론트 only) |
```

- [ ] **Step 3: 컴포넌트 지도 §2.2 프론트엔드 섹션에 신규 파일 추가**

같은 파일의 frontend 트리에 메모 파일들 삽입:

```markdown
 ├── api/
 │ ├── client.ts # fetch 래퍼
 │ ├── jobs.ts # job CRUD + 업로드 + burn
 │ ├── memo.ts # memoApi (toggleSave/update/delete/list) ← 신규
 │ ├── events.ts # EventSource 구독
 │ └── types.ts # 백엔드 schemas와 대응
 ├── stores/
 │ ├── current.ts # {screen, jobId, initialTime?, ...} ← initialTime 추가
 │ ├── history.ts # localStorage 최근 작업 + 서버 동기화
 │ ├── memos.ts # 전역 메모 리스트 (MemoListItemDto[]) ← 신규
 │ └── jobMemos.ts # 현재 Job의 segment→memo 맵 ← 신규
 ...
 └── ui/
 ├── Sidebar.svelte, BurnSheet.svelte, ClipSheet.svelte
 ├── MemoCard.svelte ← 신규 (사이드바 메모 탭 아이템)
 ├── SegmentMemo.svelte ← 신규 (세그먼트 📎 + 인라인 편집)
 ...
```

backend 트리에도 유사하게:
```markdown
backend/app/
├── api/
│ ├── memo.py # Memo REST (POST/GET/PATCH/DELETE) ← 신규
│ ...
├── services/
│ ├── memo.py # Memo CRUD + toggle + global view ← 신규
│ ...
└── models/
 ├── memo.py # Memo SQLModel ← 신규
```

- [ ] **Step 4: §3 Job 상태머신 다이어그램 하단에 "메모와 자동 pin" 한 단락 추가**

§3 마지막에 작은 섹션:

```markdown
### 3.1 메모와 자동 pin

Memo가 생성되면 `services/memo.toggle_save_memo` 가 해당 Job의 `pinned=True` 로 세팅.
TTL 만료 대상 제외 효과. 마지막 메모가 삭제돼도 pin은 자동으로 풀리지 않음
(사용자가 직접 unpin 필요). Job 삭제 시 `services/jobs.delete_job` 이
`services/memo.delete_memos_for_job` 호출하여 cascade.
```

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add docs/architecture.md
git commit -m "$(cat <<'EOF'
docs(architecture): add memo feature to component map and catalog

- 기능 카탈로그 §4에 메모 관련 6행 추가
- 컴포넌트 지도 §2에 신규 파일 (api/memo, stores/memos, jobMemos,
 ui/MemoCard, SegmentMemo, backend models/memo, services/memo, api/memo)
- §3.1 신설: 메모 auto-pin 동작 + cascade 설명
EOF
)"
```

---

### Task 6.5: master 머지

**Files:** (git ops)

- [ ] **Step 1: 최종 상태 체크**

```bash
cd /Users/loki/GenSub
git branch --show-current
git status
git log --oneline feature/memo ^master | cat
```

Expected: branch `feature/memo`, clean status, 20개 정도 커밋.

- [ ] **Step 2: pytest 마지막 그린 확인**

```bash
cd backend
uv run pytest --tb=short 2>&1 | tail -3
cd ..
```

Expected: 전부 pass.

- [ ] **Step 3: master 머지**

```bash
git checkout master
git merge --no-ff feature/memo -m "$(cat <<'EOF'
merge: memo feature — save + list + navigate (2026-04-22)

스펙: docs/superpowers/specs/2026-04-22-memo-feature-design.md
플랜: docs/superpowers/plans/2026-04-22-memo-feature/

Phase 1~5:
- 새 memo 테이블 + services/memo.py (toggle/CRUD/global liveness)
- 5개 REST 엔드포인트 (POST/GET x2/PATCH/DELETE)
- Job 삭제 시 memo cascade + 다이얼로그 경고
- 프론트: MemoDto/jobMemos/memos 스토어, SegmentMemo 컴포넌트,
 사이드바 "영상/메모" 탭, MemoCard, VideoPlayer onLoadedMetadata,
 ReadyScreen initialTime reactive seek

데이터 안전성: 새 테이블만 추가. 기존 job/segment 스키마 무변경.
init_db의 create_all로 자동 생성, 기존 데이터 무영향.
배포 전 자동 DB 백업(R6) 작동.

테스트: 기존 95 → memo feature 후 ~141 passed (46개 신규).
EOF
)" 2>&1 | tail -5
```

Expected: merge commit 생성됨.

- [ ] **Step 4: 최종 검증**

```bash
git log --oneline | head -5
git log --oneline | wc -l
```

Expected: HEAD가 새 merge commit, 전체 커밋 수는 기존 + 21개 내외.

- [ ] **Step 5: Docker 재빌드 + 기동 (최종 배포 검증)**

```bash
docker compose build 2>&1 | tail -5
docker compose up -d 2>&1 | tail -5
sleep 5
docker inspect gensub-api --format='{{.State.Health.Status}}'
docker inspect gensub-worker --format='{{.State.Health.Status}}'
curl -sS http://localhost:8000/api/health | head -c 200
curl -sS http://localhost:8000/api/memos | head -c 200
```

Expected:
- api/worker healthy
- `/api/health` 200
- `/api/memos` 는 `{"items": [...]}` (Playwright 테스트로 만든 메모가 있을 수도)

- [ ] **Step 6: (옵션) 정리**

```bash
docker compose down 2>&1 | tail -3
```

테스트 중 남긴 메모를 지우려면 DB reset 또는 UI에서 개별 삭제.

---

### Phase 6 완료 조건

- [ ] 기존 job `059ddd86…` 및 그 Segment 접근 OK (데이터 안전성)
- [ ] `memo` 테이블 자동 생성, `job`/`segment` 스키마 무변경
- [ ] pytest 전부 pass (기존 95 + 신규 memo 테스트)
- [ ] `npm run check` 0 errors, `npm run build` 성공
- [ ] `docker compose build/up` 성공, healthcheck healthy
- [ ] Playwright smoke 10단계 전부 ✅
- [ ] `docs/architecture.md` 기능 카탈로그에 메모 항목 반영
- [ ] `feature/memo` → master 머지 완료

---

## 전체 플랜 요약

| Phase | 커밋 수 | 누적 |
|---|---|---|
| 1. Backend 모델+서비스 | 4 | 4 |
| 2. Backend API+cascade | 3 | 7 |
| 3. Frontend 타입+API+스토어 | 4 | 11 |
| 4. Frontend SegmentMemo | 3 | 14 |
| 5. Frontend 사이드바+보러가기 | 5 | 19 |
| 6. 검증+문서+머지 | 2 | 21 |

**기능 완결.** 남은 Non-Goals(검색/태그/번역/내보내기)는 후속 스펙으로.
