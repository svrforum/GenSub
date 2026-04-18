# Phase 5 — 머지 + 완료 처리

목표: 리팩토링 브랜치를 master로 통합하고, 구 설계 스펙에 "현재 상태는 architecture.md 참고" 안내를 추가해 문서 체계를 명확히 한다.

---

### Task 5.1: 구 설계 스펙 상단에 안내 헤더 추가

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-gensub-design.md` — 최상단에 안내 박스

- [ ] **Step 1: 현재 상단 확인**

```bash
head -10 /Users/loki/GenSub/docs/superpowers/specs/2026-04-11-gensub-design.md
```

Expected: `# GenSub 설계 명세서`로 시작.

- [ ] **Step 2: 헤더 추가**

파일 최상단(`# GenSub 설계 명세서` 줄 **바로 앞**)에 다음 블록 삽입:

```markdown
> ℹ️ **이 문서는 2026-04-11 시점의 초기 설계 명세**입니다. 설계 의도(왜 이렇게 만들었나)를 보존하기 위해 유지되지만, **현재 구현된 아키텍처는 [`docs/architecture.md`](../../architecture.md)를 참고**하세요. 2026-04-18의 안정성 리팩토링 스펙은 [`2026-04-18-stability-refactor-design.md`](2026-04-18-stability-refactor-design.md)에 있습니다.

---

```

결과(상위 5줄):

```markdown
> ℹ️ **이 문서는 2026-04-11 시점의 초기 설계 명세**입니다. ...
...
---

# GenSub 설계 명세서
```

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add docs/superpowers/specs/2026-04-11-gensub-design.md
git commit -m "$(cat <<'EOF'
docs(spec): mark 2026-04-11 design as historical, link to current state

초기 설계 스펙은 설계 의도 보존용으로 유지하되, 상단 안내 박스로
현재 상태는 docs/architecture.md, 2026-04-18 리팩토링 스펙도 함께 안내.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5.2: `refactor/stability` → `master` 머지

**Files:** (git operation only)

- [ ] **Step 1: 브랜치 상태 최종 확인**

```bash
cd /Users/loki/GenSub
git branch --show-current
git log --oneline -10
```

Expected: 현재 `refactor/stability`, 최근 커밋들이 Phase 2~5 작업.

- [ ] **Step 2: pytest 마지막 그린 확인**

```bash
cd backend
uv run pytest --tb=short 2>&1 | tail -3
cd ..
```

Expected: 전부 pass.

- [ ] **Step 3: master 체크아웃 + 머지**

```bash
git checkout master
git merge --no-ff refactor/stability -m "$(cat <<'EOF'
merge: stability refactor + docs consolidation (2026-04-18)

Phase 2 문서 3종:
- docs/architecture.md — 현재 아키텍처 기록
- CLAUDE.md — 개발·에이전트 규약 (모델=Opus 4.7 고정 포함)
- README.md — 프로젝트 소개 + quickstart 재작성
- 루트 스크린샷 39장 정리, 2장은 docs/images/로

Phase 3 리팩토링 R1~R7:
- R1 regenerate 엔드포인트·서비스 제거 (죽은 코드)
- R2 pin_job/request_burn을 services/jobs.py로 추출
- R3 process_burn_job에 cancel 경로 + ffmpeg terminate
- R4 Sidebar TTL을 /api/config.job_ttl_hours로 연결
- R5 burn.py assert → RuntimeError
- R6 백업 로직을 services/backup.py로 분리 (worker도 호출)
- R7 compose.yaml worker healthcheck + Dockerfile procps

테스트: 35 → 38 (regenerate 삭제 1, 신규 4 — pin, request_burn,
backup, burn_cancel).

Spec: docs/superpowers/specs/2026-04-18-stability-refactor-design.md
Plan: docs/superpowers/plans/2026-04-18-stability-refactor/

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: merge commit 생성됨.

- [ ] **Step 4: 머지 후 상태**

```bash
git log --oneline | head -15
git branch -a
```

Expected:
- HEAD가 새 merge commit.
- `refactor/stability`, `feature/gensub`는 브랜치로 보존(참조용).

---

### Task 5.3: 최종 검증

**Files:** (no changes)

- [ ] **Step 1: 전체 빌드 재확인**

```bash
cd /Users/loki/GenSub
cd backend && uv run pytest --tb=short 2>&1 | tail -3 && cd ..
cd frontend && npm run check 2>&1 | tail -3 && cd ..
docker compose build 2>&1 | tail -3
```

Expected: 세 명령 모두 성공.

- [ ] **Step 2: 완료 기준(Plan README) 체크**

```bash
echo "=== commits ==="; git log --oneline | wc -l
echo "=== worktrees ==="; git worktree list
echo "=== key docs ==="; ls CLAUDE.md docs/architecture.md README.md docs/images/gensub-*.png
echo "=== root screenshots (should be 0) ==="; ls gensub-*.png 2>/dev/null | wc -l
echo "=== old spec header ==="; head -3 docs/superpowers/specs/2026-04-11-gensub-design.md
```

Expected:
- 커밋 수 ≥ 114 + Phase 2/3/5 추가분
- worktree 1개만 (메인)
- CLAUDE, architecture, README, 2개 PNG 존재
- 루트 PNG 0
- 구 스펙 상단에 `ℹ️` 안내 박스

- [ ] **Step 3: 사용자 리뷰 요청**

사용자에게 전체 작업 요약 보고:
- 완료된 리팩토링 7건 (R1~R7)
- 작성된 문서 3종
- 테스트 수 변화 (35 → 38)
- 리스크/남은 작업 (Medium 3건은 본 스코프 제외 — 다음 기회)

---

### Phase 5 완료 조건

- [ ] master에 모든 변경이 머지됨
- [ ] 구 스펙에 안내 헤더 추가
- [ ] `pytest` + `npm run check` + `docker compose build` 모두 성공
- [ ] Plan README의 "완료 기준" 체크박스 전부 ✅

작업 종료. 남은 Medium 이슈(3건)는 다음 리팩토링 사이클에서 별도 스펙으로 다룸.
