# Phase 4 — Worker Process (파이프라인 오케스트레이션)

### Task 4.1: 작업 상태/진행률 헬퍼

**Files:**
- Create: `backend/app/services/job_state.py`
- Create: `backend/tests/test_job_state.py`

- [ ] **Step 1: 실패 테스트**

Write `backend/tests/test_job_state.py`:

```python
from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus
from app.services.job_state import (
 claim_next_pending_job,
 is_cancel_requested,
 mark_failed,
 update_progress,
 update_status,
)


def _engine(tmp_path):
 e = create_db_engine(f"sqlite:///{tmp_path/'ws.db'}")
 init_db(e)
 return e


def _mk(engine, jid, st=JobStatus.pending):
 with Session(engine) as s:
 s.add(
 Job(
 id=jid,
 source_kind="url",
 source_url="https://y/x",
 model_name="small",
 status=st,
 progress=0.0,
 expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
 )
 )
 s.commit()


def test_claim_next_pending_returns_pending_and_marks_downloading(tmp_path):
 engine = _engine(tmp_path)
 _mk(engine, "a", JobStatus.ready)
 _mk(engine, "b", JobStatus.pending)
 _mk(engine, "c", JobStatus.pending)

 claimed = claim_next_pending_job(engine)
 assert claimed is not None
 assert claimed.id in ("b", "c")

 with Session(engine) as s:
 job = s.get(Job, claimed.id)
 assert job.status == JobStatus.downloading


def test_claim_returns_none_when_no_pending(tmp_path):
 engine = _engine(tmp_path)
 _mk(engine, "a", JobStatus.ready)
 assert claim_next_pending_job(engine) is None


def test_update_progress_and_status(tmp_path):
 engine = _engine(tmp_path)
 _mk(engine, "x", JobStatus.downloading)
 update_progress(engine, "x", 0.5, "음성을 듣고 있어요")
 update_status(engine, "x", JobStatus.transcribing)
 with Session(engine) as s:
 job = s.get(Job, "x")
 assert job.progress == 0.5
 assert job.stage_message == "음성을 듣고 있어요"
 assert job.status == JobStatus.transcribing


def test_mark_failed_records_error(tmp_path):
 engine = _engine(tmp_path)
 _mk(engine, "y", JobStatus.downloading)
 mark_failed(engine, "y", "boom")
 with Session(engine) as s:
 job = s.get(Job, "y")
 assert job.status == JobStatus.failed
 assert job.error_message == "boom"


def test_is_cancel_requested(tmp_path):
 engine = _engine(tmp_path)
 _mk(engine, "z", JobStatus.downloading)
 assert is_cancel_requested(engine, "z") is False
 with Session(engine) as s:
 job = s.get(Job, "z")
 job.cancel_requested = True
 s.add(job)
 s.commit()
 assert is_cancel_requested(engine, "z") is True
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_job_state.py -v`

- [ ] **Step 3: job_state 구현**

Write `backend/app/services/job_state.py`:

```python
from datetime import datetime, timezone

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.models.job import Job, JobStatus


def _now() -> datetime:
 return datetime.now(timezone.utc)


def claim_next_pending_job(engine: Engine) -> Job | None:
 """원자적으로 pending 작업 하나를 집어 downloading으로 전환."""
 with Session(engine) as s:
 row = s.exec(
 select(Job).where(Job.status == JobStatus.pending).order_by(Job.created_at)
 ).first()
 if row is None:
 return None
 row.status = JobStatus.downloading
 row.progress = 0.0
 row.stage_message = "영상을 가져오고 있어요"
 row.updated_at = _now()
 s.add(row)
 s.commit()
 s.refresh(row)
 return row


def update_progress(
 engine: Engine,
 job_id: str,
 progress: float,
 stage_message: str | None = None,
) -> None:
 with Session(engine) as s:
 job = s.get(Job, job_id)
 if job is None:
 return
 job.progress = max(0.0, min(1.0, progress))
 if stage_message is not None:
 job.stage_message = stage_message
 job.updated_at = _now()
 s.add(job)
 s.commit()


def update_status(
 engine: Engine,
 job_id: str,
 status: JobStatus,
 stage_message: str | None = None,
) -> None:
 with Session(engine) as s:
 job = s.get(Job, job_id)
 if job is None:
 return
 job.status = status
 if stage_message is not None:
 job.stage_message = stage_message
 job.progress = 0.0
 job.updated_at = _now()
 s.add(job)
 s.commit()


def update_title_and_duration(
 engine: Engine,
 job_id: str,
 title: str | None,
 duration_sec: float | None,
) -> None:
 with Session(engine) as s:
 job = s.get(Job, job_id)
 if job is None:
 return
 if title:
 job.title = title
 if duration_sec is not None:
 job.duration_sec = duration_sec
 job.updated_at = _now()
 s.add(job)
 s.commit()


def update_language(engine: Engine, job_id: str, language: str) -> None:
 with Session(engine) as s:
 job = s.get(Job, job_id)
 if job is None:
 return
 job.language = language
 job.updated_at = _now()
 s.add(job)
 s.commit()


def mark_failed(engine: Engine, job_id: str, error_message: str) -> None:
 with Session(engine) as s:
 job = s.get(Job, job_id)
 if job is None:
 return
 job.status = JobStatus.failed
 job.error_message = error_message
 job.updated_at = _now()
 s.add(job)
 s.commit()


def mark_ready(engine: Engine, job_id: str) -> None:
 with Session(engine) as s:
 job = s.get(Job, job_id)
 if job is None:
 return
 job.status = JobStatus.ready
 job.progress = 1.0
 job.stage_message = "준비됐어요"
 job.updated_at = _now()
 s.add(job)
 s.commit()


def mark_done(engine: Engine, job_id: str) -> None:
 with Session(engine) as s:
 job = s.get(Job, job_id)
 if job is None:
 return
 job.status = JobStatus.done
 job.progress = 1.0
 job.stage_message = "완료됐어요"
 job.updated_at = _now()
 s.add(job)
 s.commit()


def is_cancel_requested(engine: Engine, job_id: str) -> bool:
 with Session(engine) as s:
 job = s.get(Job, job_id)
 return bool(job and job.cancel_requested)


def claim_burn_job(engine: Engine) -> Job | None:
 """ready 상태에서 burn 요청된 작업을 burning으로 전환."""
 with Session(engine) as s:
 row = s.exec(
 select(Job)
 .where(Job.status == JobStatus.burning, Job.progress == 0.0)
 .order_by(Job.updated_at)
 ).first()
 return row
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_job_state.py -v`
Expected: 5 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/job_state.py backend/tests/test_job_state.py
git commit -m "feat(backend): add worker-side job state helpers"
```

---

### Task 4.2: 파이프라인 오케스트레이터

**Files:**
- Create: `backend/app/services/pipeline.py`
- Create: `backend/tests/test_pipeline_orchestration.py`

- [ ] **Step 1: 실패 테스트 — 모킹한 다운로드/전사로 전 흐름 검증**

Write `backend/tests/test_pipeline_orchestration.py`:

```python
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.models.job import Job, JobStatus
from app.services.pipeline import process_job
from app.services.subtitles import SegmentData
from app.services.downloader import DownloadResult
from app.services.transcriber import TranscribeResult


def _make(tmp_path, monkeypatch):
 monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
 monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
 settings = Settings(database_url=f"sqlite:///{tmp_path/'p.db'}")
 engine = create_db_engine(settings.database_url)
 init_db(engine)
 return settings, engine


def test_process_job_happy_path(tmp_path, monkeypatch):
 settings, engine = _make(tmp_path, monkeypatch)
 job_id = "j1"
 with Session(engine) as s:
 s.add(
 Job(
 id=job_id,
 source_kind="url",
 source_url="https://y/x",
 model_name="small",
 status=JobStatus.downloading,
 progress=0.0,
 expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
 )
 )
 s.commit()

 media = settings.media_dir / job_id
 media.mkdir(parents=True, exist_ok=True)
 fake_source = media / "source.mp4"
 fake_source.write_bytes(b"0")
 fake_audio = media / "audio.wav"
 fake_audio.write_bytes(b"0")

 with patch(
 "app.services.pipeline.download_video",
 return_value=DownloadResult(path=fake_source, title="t", duration=10.0),
 ), patch(
 "app.services.pipeline.extract_audio",
 return_value=fake_audio,
 ), patch(
 "app.services.pipeline.transcribe",
 return_value=TranscribeResult(
 segments=[SegmentData(idx=0, start=0.0, end=3.0, text="hi")],
 language="en",
 duration=10.0,
 ),
 ):
 process_job(settings=settings, engine=engine, job_id=job_id)

 with Session(engine) as s:
 job = s.get(Job, job_id)
 assert job.status == JobStatus.ready
 assert job.language == "en"
 assert job.duration_sec == 10.0

 assert (media / "subtitles.srt").exists()
 assert (media / "subtitles.vtt").exists()


def test_process_job_failure_marks_failed(tmp_path, monkeypatch):
 settings, engine = _make(tmp_path, monkeypatch)
 job_id = "j2"
 with Session(engine) as s:
 s.add(
 Job(
 id=job_id,
 source_kind="url",
 source_url="https://y/x",
 model_name="small",
 status=JobStatus.downloading,
 progress=0.0,
 expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
 )
 )
 s.commit()

 with patch(
 "app.services.pipeline.download_video",
 side_effect=RuntimeError("video unavailable"),
 ):
 process_job(settings=settings, engine=engine, job_id=job_id)

 with Session(engine) as s:
 job = s.get(Job, job_id)
 assert job.status == JobStatus.failed
 assert "video unavailable" in (job.error_message or "")
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_pipeline_orchestration.py -v`

- [ ] **Step 3: pipeline.py 구현**

Write `backend/app/services/pipeline.py`:

```python
from pathlib import Path

from sqlalchemy.engine import Engine

from app.core.settings import Settings
from app.models.job import JobStatus
from app.services import job_state
from app.services.audio import extract_audio
from app.services.downloader import download_video
from app.services.segments import replace_all_segments
from app.services.subtitles import format_srt, format_vtt, SegmentData
from app.services.transcriber import transcribe


class JobCancelled(Exception):
 pass


def _check_cancel(engine: Engine, job_id: str) -> None:
 if job_state.is_cancel_requested(engine, job_id):
 raise JobCancelled(job_id)


def _write_subtitle_files(media_dir: Path, segments: list[SegmentData]) -> None:
 (media_dir / "subtitles.srt").write_text(format_srt(segments), encoding="utf-8")
 (media_dir / "subtitles.vtt").write_text(format_vtt(segments), encoding="utf-8")


def process_job(settings: Settings, engine: Engine, job_id: str) -> None:
 media_dir = settings.media_dir / job_id
 media_dir.mkdir(parents=True, exist_ok=True)

 try:
 # --- 1. 다운로드 ---
 job_state.update_progress(engine, job_id, 0.0, "영상을 가져오고 있어요")

 def dl_progress(pct: float) -> None:
 job_state.update_progress(engine, job_id, pct)

 from sqlmodel import Session
 from app.models.job import Job

 with Session(engine) as s:
 job = s.get(Job, job_id)
 if job is None:
 return
 source_kind = job.source_kind
 source_url = job.source_url
 model_name = job.model_name
 language_override = job.language
 initial_prompt = job.initial_prompt

 if source_kind == "url":
 if not source_url:
 raise RuntimeError("url missing")
 result = download_video(
 url=source_url, dest_dir=media_dir, progress_callback=dl_progress
 )
 job_state.update_title_and_duration(
 engine, job_id, result.title, result.duration
 )
 source_path = result.path
 else:
 candidates = list(media_dir.glob("source.*"))
 if not candidates:
 raise RuntimeError("uploaded source file missing")
 source_path = candidates[0]

 _check_cancel(engine, job_id)

 # --- 2. 음성 추출 ---
 job_state.update_status(engine, job_id, JobStatus.transcribing, "음성을 듣고 있어요")
 audio_path = extract_audio(source_path, media_dir / "audio.wav")

 _check_cancel(engine, job_id)

 # --- 3. 전사 ---
 def tr_progress(pct: float) -> None:
 job_state.update_progress(engine, job_id, pct)

 tr_result = transcribe(
 audio_path=audio_path,
 model_name=model_name,
 compute_type=settings.compute_type,
 model_cache_dir=settings.model_cache_dir,
 language=language_override,
 initial_prompt=initial_prompt,
 progress_callback=tr_progress,
 )
 job_state.update_language(engine, job_id, tr_result.language)

 _check_cancel(engine, job_id)

 # --- 4. 저장 + ready ---
 replace_all_segments(engine, job_id, tr_result.segments)
 _write_subtitle_files(media_dir, tr_result.segments)
 job_state.mark_ready(engine, job_id)

 except JobCancelled:
 job_state.mark_failed(engine, job_id, "사용자가 작업을 취소했어요")
 except Exception as exc:
 job_state.mark_failed(engine, job_id, str(exc))
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_pipeline_orchestration.py -v`
Expected: 2 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/pipeline.py backend/tests/test_pipeline_orchestration.py
git commit -m "feat(backend): add pipeline orchestrator (download → extract → transcribe → ready)"
```

---

### Task 4.3: Burn-in 파이프라인

**Files:**
- Modify: `backend/app/services/pipeline.py`
- Create: `backend/tests/test_pipeline_burn.py`

- [ ] **Step 1: 실패 테스트**

Write `backend/tests/test_pipeline_burn.py`:

```python
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.models.job import Job, JobStatus
from app.services.pipeline import process_burn_job
from app.services.segments import replace_all_segments
from app.services.subtitles import SegmentData


def test_process_burn_creates_output_and_marks_done(tmp_path, monkeypatch):
 monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
 monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
 settings = Settings(database_url=f"sqlite:///{tmp_path/'b.db'}")
 engine = create_db_engine(settings.database_url)
 init_db(engine)

 job_id = "jb"
 with Session(engine) as s:
 s.add(
 Job(
 id=job_id,
 source_kind="url",
 source_url="https://y/x",
 model_name="small",
 status=JobStatus.burning,
 progress=0.0,
 duration_sec=10.0,
 expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
 )
 )
 s.commit()

 media = settings.media_dir / job_id
 media.mkdir(parents=True, exist_ok=True)
 (media / "source.mp4").write_bytes(b"0")
 replace_all_segments(
 engine, job_id, [SegmentData(idx=0, start=0.0, end=2.0, text="hi")]
 )

 with patch("app.services.pipeline.burn_video") as mock_burn:
 def _fake(video, ass, output, total_duration_sec, progress_callback=None):
 output.write_bytes(b"burned")
 return output
 mock_burn.side_effect = _fake
 process_burn_job(settings=settings, engine=engine, job_id=job_id)

 assert (media / "burned.mp4").exists()
 with Session(engine) as s:
 job = s.get(Job, job_id)
 assert job.status == JobStatus.done
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_pipeline_burn.py -v`

- [ ] **Step 3: process_burn_job 함수 추가**

Append to `backend/app/services/pipeline.py`:

```python
from app.services.ass_style import BurnStyle, srt_segments_to_ass
from app.services.burn import burn_video
from app.services.segments import load_segments


def process_burn_job(
 settings: Settings,
 engine: Engine,
 job_id: str,
 style: BurnStyle | None = None,
) -> None:
 from sqlmodel import Session
 from app.models.job import Job

 media_dir = settings.media_dir / job_id

 try:
 with Session(engine) as s:
 job = s.get(Job, job_id)
 if job is None:
 return
 duration = job.duration_sec or 1.0

 source_candidates = list(media_dir.glob("source.*"))
 if not source_candidates:
 raise RuntimeError("source video missing")
 source = source_candidates[0]

 segments = load_segments(engine, job_id)
 ass_path = media_dir / "subtitles.ass"
 ass_path.write_text(
 srt_segments_to_ass(segments, style or BurnStyle()),
 encoding="utf-8",
 )

 job_state.update_progress(engine, job_id, 0.0, "자막을 영상에 입히고 있어요")

 def burn_progress(pct: float) -> None:
 job_state.update_progress(engine, job_id, pct)

 output = media_dir / "burned.mp4"
 burn_video(
 video=source,
 ass=ass_path,
 output=output,
 total_duration_sec=duration,
 progress_callback=burn_progress,
 )
 job_state.mark_done(engine, job_id)
 except Exception as exc:
 job_state.mark_failed(engine, job_id, str(exc))
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_pipeline_burn.py -v`
Expected: 1 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/pipeline.py backend/tests/test_pipeline_burn.py
git commit -m "feat(backend): add burn-in pipeline function"
```

---

### Task 4.4: 워커 메인 루프

**Files:**
- Create: `backend/worker/__init__.py`
- Create: `backend/worker/main.py`
- Create: `backend/tests/test_worker_main.py`

- [ ] **Step 1: 통합 테스트**

Write `backend/tests/test_worker_main.py`:

```python
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings
from app.models.job import Job, JobStatus
from app.services.downloader import DownloadResult
from app.services.subtitles import SegmentData
from app.services.transcriber import TranscribeResult


def test_worker_tick_picks_pending_and_processes(tmp_path, monkeypatch):
 monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
 monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
 settings = Settings(database_url=f"sqlite:///{tmp_path/'w.db'}")
 engine = create_db_engine(settings.database_url)
 init_db(engine)

 jid = "wj"
 with Session(engine) as s:
 s.add(
 Job(
 id=jid,
 source_kind="url",
 source_url="https://y/x",
 model_name="small",
 status=JobStatus.pending,
 progress=0.0,
 expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
 )
 )
 s.commit()

 media = settings.media_dir / jid
 media.mkdir(parents=True, exist_ok=True)
 (media / "source.mp4").write_bytes(b"0")
 (media / "audio.wav").write_bytes(b"0")

 with patch(
 "app.services.pipeline.download_video",
 return_value=DownloadResult(
 path=media / "source.mp4", title="x", duration=5.0
 ),
 ), patch(
 "app.services.pipeline.extract_audio",
 return_value=media / "audio.wav",
 ), patch(
 "app.services.pipeline.transcribe",
 return_value=TranscribeResult(
 segments=[SegmentData(idx=0, start=0.0, end=1.0, text="x")],
 language="en",
 duration=5.0,
 ),
 ):
 from worker.main import tick

 did = tick(settings, engine)
 assert did is True

 with Session(engine) as s:
 job = s.get(Job, jid)
 assert job.status == JobStatus.ready


def test_worker_tick_no_job_returns_false(tmp_path, monkeypatch):
 monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
 monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
 settings = Settings(database_url=f"sqlite:///{tmp_path/'w2.db'}")
 engine = create_db_engine(settings.database_url)
 init_db(engine)

 from worker.main import tick
 assert tick(settings, engine) is False
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_worker_main.py -v`

- [ ] **Step 3: 워커 엔트리포인트 구현**

Write `backend/worker/__init__.py` (빈 파일):

```python
```

Write `backend/worker/main.py`:

```python
import signal
import time

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.db import create_db_engine, init_db
from app.core.settings import Settings, get_settings
from app.models.job import Job, JobStatus
from app.services import job_state
from app.services.pipeline import process_burn_job, process_job

POLL_INTERVAL_SEC = 1.5

_stop_requested = False


def _handle_signal(*_args) -> None:
 global _stop_requested
 _stop_requested = True


def _find_burn_candidate(engine: Engine) -> Job | None:
 with Session(engine) as s:
 return s.exec(
 select(Job)
 .where(Job.status == JobStatus.burning)
 .where(Job.progress == 0.0)
 .order_by(Job.updated_at)
 ).first()


def tick(settings: Settings, engine: Engine) -> bool:
 burn = _find_burn_candidate(engine)
 if burn is not None:
 process_burn_job(settings=settings, engine=engine, job_id=burn.id)
 return True

 claimed = job_state.claim_next_pending_job(engine)
 if claimed is not None:
 process_job(settings=settings, engine=engine, job_id=claimed.id)
 return True

 return False


def run() -> None:
 signal.signal(signal.SIGTERM, _handle_signal)
 signal.signal(signal.SIGINT, _handle_signal)

 settings = get_settings()
 engine = create_db_engine(settings.database_url)
 init_db(engine)

 print(f"[worker] starting (role={settings.gensub_role}, model={settings.default_model})", flush=True)

 while not _stop_requested:
 try:
 did_work = tick(settings, engine)
 except Exception as exc:
 print(f"[worker] tick error: {exc}", flush=True)
 did_work = False
 if not did_work:
 time.sleep(POLL_INTERVAL_SEC)

 print("[worker] shutting down", flush=True)


if __name__ == "__main__":
 run()
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_worker_main.py -v`
Expected: 2 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/worker/ backend/tests/test_worker_main.py
git commit -m "feat(worker): add main polling loop with pending + burn handling"
```

---

