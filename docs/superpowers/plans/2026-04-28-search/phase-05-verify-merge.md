# Phase 5 — 통합 검증 + 문서 + 머지

목표: 전체 테스트, Docker 재빌드, Playwright UI smoke, `docs/architecture.md` 업데이트, master 머지 + GitHub push.

**전제**: Phase 1~4 완료. 백엔드 157, 프론트 빌드 OK.

---

### Task 5.1: 백엔드 + 프론트 테스트 + 빌드

**Files:** (no changes)

- [ ] **Step 1: 백엔드 pytest**

```bash
cd /Users/loki/GenSub/backend
uv run pytest --tb=short 2>&1 | tail -10
```

Expected: 157 passed.

- [ ] **Step 2: ruff**

```bash
uv run ruff check app/ tests/ 2>&1 | tail -5
```

Expected: 통과 (또는 기존 수준 warnings).

- [ ] **Step 3: 프론트 체크 + 빌드 + 테스트**

```bash
cd ../frontend
npx svelte-kit sync 2>&1 | tail -3
npm run check 2>&1 | tail -5
npm run build 2>&1 | tail -5
npm test 2>&1 | tail -5
```

Expected: 0 errors, 빌드 성공, 4 tests pass.

---

### Task 5.2: Docker 재빌드 + 헬스체크

**Files:** (no changes)

- [ ] **Step 1: 재빌드**

```bash
cd /Users/loki/GenSub
docker compose down 2>&1 | tail -3
docker compose build 2>&1 | tail -5
docker compose up -d 2>&1 | tail -5
```

- [ ] **Step 2: 헬스 + search 엔드포인트 확인**

```bash
until curl -fsS http://localhost:8000/api/health > /dev/null 2>&1; do sleep 1; done
echo "ready"
curl -fsS 'http://localhost:8000/api/search?q=' | python3 -m json.tool
curl -fsS 'http://localhost:8000/api/search?q=hello' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'items count={len(d[\"items\"])}')"
```

Expected:
- `q=` → `{"items": []}`
- `q=hello` → 200, items count는 데이터에 따라 다름

---

### Task 5.3: Playwright UI smoke

**Files:** (no changes)

브라우저로 http://localhost:8000 접속. 다음 단계 확인:

- [ ] **Step 1: 헤더 SearchBar 보임**

기본 화면(Idle 또는 Ready) 어디서든 헤더 가운데에 "자막·메모·영상 검색…" placeholder 와 ⌘K 단축키 표시되는 검색바 있는지.

- [ ] **Step 2: 헤더바 클릭 → 모달**

검색바 클릭 → 화면 중앙에 모달 오픈. 자동 포커스. Esc 로 닫힘 확인.

- [ ] **Step 3: ⌘K 단축키 (Mac) / Ctrl+K (Linux/Windows)**

화면 어디서든 단축키 → 모달 오픈.

- [ ] **Step 4: 검색 결과**

모달 입력에 기존 영상 자막의 단어 (예: "Movies" — 기존 영상에 있던 단어) 입력 → 200ms 후 결과 카드 나타남. 카드에 자막 텍스트 + 영상 제목 + MM:SS 표시.

- [ ] **Step 5: 결과 클릭 → 점프**

자막 매치 카드 클릭 → 모달 닫히고 해당 영상의 ReadyScreen 으로 이동 + 해당 시점 영상 seek 됨.

- [ ] **Step 6: ⌘F (Mac) / Ctrl+F (Linux) 영상 내**

ReadyScreen 진입 후 ⌘F → 우상단에 작은 검색 오버레이 노출. 단어 입력 → 매치된 세그먼트 노란 강조 + N/M 카운트.

- [ ] **Step 7: ⌘F Enter 점프**

오버레이에서 Enter → 다음 매치로 영상 seek + 세그먼트 스크롤. Shift+Enter → 이전 매치.

- [ ] **Step 8: ⌘F Esc**

Esc → 오버레이 닫힘 + 매치 강조 해제.

- [ ] **Step 9: Playwright 스크린샷 (옵션)**

```
docs/images/test-search-01-modal.png
docs/images/test-search-02-results.png
docs/images/test-search-03-in-video.png
```

Playwright MCP 로 캡처 (선택).

- [ ] **Step 10: 정리**

```bash
docker compose down 2>&1 | tail -3
```

(or 그대로 두기)

---

### Task 5.4: docs/architecture.md 업데이트

**Files:**
- Modify: `docs/architecture.md`

- [ ] **Step 1: §4 기능 카탈로그 표에 검색 행 추가**

`docs/architecture.md` 의 §4 기능 카탈로그 표 끝부분에 다음 행 추가 (키보드 단축키 행 위 또는 메모 카탈로그 직후):

```markdown
| 전역 검색 (자막+메모+영상) | `SearchBar.svelte` + `SearchModal.svelte` (헤더 + ⌘K 모달) | `GET /api/search` | `services/search.search_all` |
| 영상 내 자막 검색 (⌘F) | `InVideoSearchOverlay.svelte` (ReadyScreen) | - (클라이언트 사이드) | - |
```

- [ ] **Step 2: §2 컴포넌트 지도에 신규 파일 추가**

backend 트리에:

```
├── api/
│   ├── search.py                # GET /api/search ← 신규
│   ...
├── services/
│   ├── search.py                # search_all + SearchHit ← 신규
│   ...
```

frontend 트리에:

```
├── api/
│   ├── search.ts                # searchApi.query ← 신규
│   ...
├── stores/
│   ├── search.ts                # searchOpen/Query/Results/Loading + scheduleSearch ← 신규
│   ...
└── ui/
    ├── SearchBar.svelte         # 헤더 항상 보이는 검색바 ← 신규
    ├── SearchModal.svelte       # ⌘K 글로벌 검색 모달 ← 신규
    ├── InVideoSearchOverlay.svelte # ReadyScreen ⌘F 영상 내 검색 ← 신규
    ...
```

- [ ] **Step 3: §5.2 REST 엔드포인트 표에 추가**

```markdown
| GET | `/api/search?q=&limit=` | 자막·메모·영상 통합 검색 (LIKE 부분 매치) |
```

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add docs/architecture.md
git commit -m "docs(architecture): add search feature to component map and catalog

§2 컴포넌트 지도: backend api/search.py + services/search.py +
frontend api/search.ts + stores/search.ts + 3 새 UI 컴포넌트
(SearchBar/SearchModal/InVideoSearchOverlay).

§4 기능 카탈로그: 전역 검색 + 영상 내 검색 행 추가.
§5.2 REST 엔드포인트 표에 GET /api/search 추가."
```

---

### Task 5.5: master 머지 + GitHub push

**Files:** (git ops only)

- [ ] **Step 1: 마지막 회귀 확인**

```bash
cd /Users/loki/GenSub
git status
cd backend && uv run pytest --tb=short 2>&1 | tail -3 && cd ..
cd frontend && npm run check 2>&1 | tail -3 && cd ..
```

Expected: clean status, 157 backend tests pass, 0 frontend errors.

- [ ] **Step 2: master 체크아웃 + 머지**

```bash
git checkout master
git merge --no-ff feature/search -m "merge: search feature (global ⌘K + in-video ⌘F)

Spec: docs/superpowers/specs/2026-04-28-search-design.md
Plan: docs/superpowers/plans/2026-04-28-search/

기능:
- GET /api/search 엔드포인트 (자막+메모+영상 LIKE 매치)
- 헤더 SearchBar 항상 visible + ⌘K 글로벌 모달
- ReadyScreen 안 ⌘F 오버레이 + 매치 강조 + Enter/↑↓ 점프
- 결과 클릭 → openMemo 흐름으로 영상 + 시점 점프

데이터 안전성: 새 테이블/컬럼/인덱스 0. 스키마 무변경.
테스트: 142 → 157 backend (15 신규)."
```

- [ ] **Step 3: GitHub push**

```bash
git push origin master 2>&1 | tail -5
```

Expected: master push 완료.

- [ ] **Step 4: 최종 확인**

```bash
git log --oneline | head -5
echo "---remote---"
git ls-remote --heads origin
```

Expected: master HEAD가 새 merge commit, origin master가 same SHA.

---

### Phase 5 완료 조건

- [ ] 백엔드 pytest 157 passed
- [ ] 프론트 svelte-check 0 errors, vitest 4 passed, build success
- [ ] Docker compose 재빌드 + healthcheck healthy
- [ ] `/api/search?q=` 와 `/api/search?q=hello` 정상 응답
- [ ] Playwright smoke 8 단계 모두 ✅
- [ ] `docs/architecture.md` 검색 항목 반영
- [ ] `feature/search` → master 머지
- [ ] GitHub `origin/master` push 완료

작업 종료. 후속 작업이 필요해지면 별도 스펙 (FTS5 마이그레이션 / 검색 히스토리 등).
