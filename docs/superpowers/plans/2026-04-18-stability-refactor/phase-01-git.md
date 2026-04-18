# Phase 1 — Git 정리

목표: `feature/gensub` worktree의 111커밋을 master로 통합하고, 이후 리팩토링을 위한 `refactor/stability` 브랜치를 만든다.

---

### Task 1.1: 시작 상태 기록

**Files:** (no changes)

- [ ] **Step 1: 현재 master 커밋 기록**

```bash
cd /Users/loki/GenSub
git log --oneline -5 > /tmp/master-before-merge.txt
git log --oneline master | wc -l
```

Expected: 4 (초기 3개 + 2026-04-18 스펙 2개)

- [ ] **Step 2: feature/gensub 커밋 수 기록**

```bash
git -C .worktrees/gensub-impl log --oneline | wc -l
```

Expected: 111 또는 그 이상

- [ ] **Step 3: worktree의 pytest 그린 확인 (머지 전 기준선)**

```bash
cd /Users/loki/GenSub/.worktrees/gensub-impl/backend
uv run pytest --tb=short 2>&1 | tail -20
```

Expected: 전부 pass. 실패 케이스가 있으면 여기서 멈추고 사용자와 상의.

- [ ] **Step 4: 작업 공간 청소 확인**

```bash
cd /Users/loki/GenSub
git status --short
git -C .worktrees/gensub-impl status --short
```

Expected: 둘 다 clean (uncommitted 없음). 스크린샷 PNG들은 untracked로 보일 수 있음 — 정상 (Phase 2에서 처리).

---

### Task 1.2: feature/gensub → master 일반 머지

**Files:** (git operations only)

- [ ] **Step 1: master 체크아웃 확인**

```bash
cd /Users/loki/GenSub
git branch --show-current
```

Expected: `master`

- [ ] **Step 2: merge 실행**

```bash
git merge --no-ff feature/gensub -m "$(cat <<'EOF'
merge: integrate feature/gensub (111 commits of iterative implementation)

백엔드(FastAPI + worker + SQLite) + 프론트엔드(SvelteKit) + Docker 스택의
완전한 구현체를 master로 통합. worktree 기반으로 진행된 반복 개선
히스토리를 모두 보존하기 위해 squash 아닌 일반 merge.
EOF
)"
```

Expected: merge commit이 생성됨. 충돌이 발생하면 `.worktrees/` 관련은 master 쪽 유지, 그 외는 피쳐 브랜치 쪽.

- [ ] **Step 3: 머지 결과 검증**

```bash
git log --oneline | wc -l
ls backend/ frontend/ compose.yaml Dockerfile 2>&1
```

Expected:
- 커밋 수 ≥ 114
- `backend/`, `frontend/`, `compose.yaml`, `Dockerfile` 모두 존재

---

### Task 1.3: worktree 제거

**Files:** (no file edits, git worktree ops)

- [ ] **Step 1: worktree 목록 확인**

```bash
git worktree list
```

Expected: `/Users/loki/GenSub/.worktrees/gensub-impl [feature/gensub]` 표시.

- [ ] **Step 2: worktree 제거**

```bash
git worktree remove .worktrees/gensub-impl
ls .worktrees/ 2>&1 || echo "디렉토리 없음 OK"
```

Expected: `.worktrees/gensub-impl` 제거됨. `.worktrees/` 디렉토리 자체가 비어있거나 존재하지 않음.

- [ ] **Step 3: feature/gensub 브랜치 보존 확인**

```bash
git branch -a | grep gensub
```

Expected: `feature/gensub` 남아있음 (삭제하지 않음 — 롤백용).

---

### Task 1.4: refactor/stability 브랜치 생성

**Files:** (no file edits)

- [ ] **Step 1: master에서 새 브랜치 생성**

```bash
cd /Users/loki/GenSub
git checkout -b refactor/stability
git branch --show-current
```

Expected: `refactor/stability`

- [ ] **Step 2: 브랜치 상태 확인**

```bash
git log --oneline -3
```

Expected: 방금 머지한 merge commit이 HEAD.

---

### Task 1.5: Phase 1 완료 검증

**Files:** (no file edits)

- [ ] **Step 1: 전체 상태 요약 출력**

```bash
cd /Users/loki/GenSub
echo "=== branch ==="
git branch --show-current
echo "=== worktrees ==="
git worktree list
echo "=== commits ==="
git log --oneline | wc -l
echo "=== structure ==="
ls backend/app/main.py frontend/src/routes/+page.svelte compose.yaml
```

Expected:
- branch: `refactor/stability`
- worktrees: main 하나만
- commits ≥ 114
- 세 파일 전부 존재

- [ ] **Step 2: 백엔드 테스트 재실행 (머지 후에도 동일하게 그린인지)**

```bash
cd backend
uv run pytest --tb=short 2>&1 | tail -5
```

Expected: 기존 pytest 결과와 동일. 머지로 바뀐 건 없으니 모두 pass.

Phase 1 완료. Phase 2 진행 가능.
