# Phase 3 — Pipeline Services (파이프라인 순수 함수들)

Phase 3의 서비스들은 모두 워커가 호출하는 순수 함수로, 외부 바이너리(yt-dlp, ffmpeg, mkvmerge, faster-whisper)를 래핑한다. 각 서비스는 진행률 콜백을 받아 DB 업데이트를 가능하게 한다.

### Task 3.1: 자막 파일 작성기 (SRT / VTT / TXT / JSON)

**Files:**
- Create: `backend/app/services/subtitles.py`
- Create: `backend/tests/test_subtitles.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_subtitles.py`:

```python
from app.services.subtitles import (
 format_srt,
 format_vtt,
 format_txt,
 format_json,
 SegmentData,
)


SEGMENTS = [
 SegmentData(idx=0, start=0.0, end=3.5, text="안녕하세요"),
 SegmentData(idx=1, start=3.5, end=7.25, text="반갑습니다"),
]


def test_format_srt():
 out = format_srt(SEGMENTS)
 assert "1\n00:00:00,000 --> 00:00:03,500\n안녕하세요" in out
 assert "2\n00:00:03,500 --> 00:00:07,250\n반갑습니다" in out


def test_format_vtt():
 out = format_vtt(SEGMENTS)
 assert out.startswith("WEBVTT\n")
 assert "00:00:00.000 --> 00:00:03.500" in out
 assert "안녕하세요" in out


def test_format_txt_is_plain_lines():
 out = format_txt(SEGMENTS)
 assert out == "안녕하세요\n반갑습니다\n"


def test_format_json_contains_timestamps():
 import json as _json
 out = format_json(SEGMENTS)
 data = _json.loads(out)
 assert data["segments"][0]["start"] == 0.0
 assert data["segments"][1]["text"] == "반갑습니다"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_subtitles.py -v`

- [ ] **Step 3: subtitles 모듈 구현**

Write `backend/app/services/subtitles.py`:

```python
import json
from dataclasses import dataclass
from typing import Iterable


@dataclass
class SegmentData:
 idx: int
 start: float
 end: float
 text: str
 avg_logprob: float | None = None
 no_speech_prob: float | None = None


def _ts_srt(t: float) -> str:
 h = int(t // 3600)
 m = int((t % 3600) // 60)
 s = int(t % 60)
 ms = int(round((t - int(t)) * 1000))
 return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _ts_vtt(t: float) -> str:
 h = int(t // 3600)
 m = int((t % 3600) // 60)
 s = int(t % 60)
 ms = int(round((t - int(t)) * 1000))
 return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def format_srt(segments: Iterable[SegmentData]) -> str:
 lines = []
 for seg in segments:
 lines.append(str(seg.idx + 1))
 lines.append(f"{_ts_srt(seg.start)} --> {_ts_srt(seg.end)}")
 lines.append(seg.text)
 lines.append("")
 return "\n".join(lines)


def format_vtt(segments: Iterable[SegmentData]) -> str:
 lines = ["WEBVTT", ""]
 for seg in segments:
 lines.append(f"{_ts_vtt(seg.start)} --> {_ts_vtt(seg.end)}")
 lines.append(seg.text)
 lines.append("")
 return "\n".join(lines)


def format_txt(segments: Iterable[SegmentData]) -> str:
 return "".join(seg.text + "\n" for seg in segments)


def format_json(segments: Iterable[SegmentData]) -> str:
 data = {
 "segments": [
 {
 "idx": s.idx,
 "start": s.start,
 "end": s.end,
 "text": s.text,
 "avg_logprob": s.avg_logprob,
 "no_speech_prob": s.no_speech_prob,
 }
 for s in segments
 ]
 }
 return json.dumps(data, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_subtitles.py -v`
Expected: 4 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/subtitles.py backend/tests/test_subtitles.py
git commit -m "feat(backend): add subtitle formatters (SRT/VTT/TXT/JSON)"
```

---

### Task 3.2: 세그먼트 저장/로드 헬퍼

**Files:**
- Create: `backend/app/services/segments.py`
- Create: `backend/tests/test_segments_service.py`

- [ ] **Step 1: 실패 테스트 작성**

Write `backend/tests/test_segments_service.py`:

```python
from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.core.db import create_db_engine, init_db
from app.models.job import Job, JobStatus
from app.services.segments import (
 load_segments,
 replace_all_segments,
 search_and_replace,
 update_segment,
)
from app.services.subtitles import SegmentData


def _engine(tmp_path):
 e = create_db_engine(f"sqlite:///{tmp_path/'s.db'}")
 init_db(e)
 return e


def _mk_job(engine, job_id="j"):
 with Session(engine) as s:
 s.add(
 Job(
 id=job_id,
 source_kind="url",
 source_url="https://y/x",
 model_name="small",
 status=JobStatus.ready,
 progress=1.0,
 expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
 )
 )
 s.commit()


def test_replace_all_and_load(tmp_path):
 engine = _engine(tmp_path)
 _mk_job(engine)
 segs = [
 SegmentData(idx=0, start=0.0, end=2.0, text="hi"),
 SegmentData(idx=1, start=2.0, end=4.0, text="there"),
 ]
 replace_all_segments(engine, "j", segs)
 loaded = load_segments(engine, "j")
 assert [s.text for s in loaded] == ["hi", "there"]


def test_update_segment_marks_edited(tmp_path):
 engine = _engine(tmp_path)
 _mk_job(engine)
 replace_all_segments(
 engine,
 "j",
 [SegmentData(idx=0, start=0.0, end=1.0, text="hi")],
 )
 update_segment(engine, "j", 0, text="hello", start=0.1, end=1.2)
 loaded = load_segments(engine, "j")
 assert loaded[0].text == "hello"
 assert loaded[0].start == 0.1
 assert loaded[0].end == 1.2


def test_search_and_replace_counts(tmp_path):
 engine = _engine(tmp_path)
 _mk_job(engine)
 replace_all_segments(
 engine,
 "j",
 [
 SegmentData(idx=0, start=0.0, end=1.0, text="트렌스포머"),
 SegmentData(idx=1, start=1.0, end=2.0, text="트렌스포머 이야기"),
 SegmentData(idx=2, start=2.0, end=3.0, text="그 외 내용"),
 ],
 )
 n = search_and_replace(engine, "j", find="트렌스포머", replace="트랜스포머")
 assert n == 2
 loaded = load_segments(engine, "j")
 assert loaded[0].text == "트랜스포머"
 assert loaded[1].text == "트랜스포머 이야기"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_segments_service.py -v`

- [ ] **Step 3: segments 서비스 구현**

Write `backend/app/services/segments.py`:

```python
from sqlalchemy.engine import Engine
from sqlmodel import Session, delete, select

from app.models.segment import Segment
from app.services.subtitles import SegmentData


def replace_all_segments(engine: Engine, job_id: str, segments: list[SegmentData]) -> None:
 with Session(engine) as s:
 s.exec(delete(Segment).where(Segment.job_id == job_id))
 for seg in segments:
 s.add(
 Segment(
 job_id=job_id,
 idx=seg.idx,
 start=seg.start,
 end=seg.end,
 text=seg.text,
 avg_logprob=seg.avg_logprob,
 no_speech_prob=seg.no_speech_prob,
 edited=False,
 )
 )
 s.commit()


def load_segments(engine: Engine, job_id: str) -> list[SegmentData]:
 with Session(engine) as s:
 rows = s.exec(
 select(Segment).where(Segment.job_id == job_id).order_by(Segment.idx)
 ).all()
 return [
 SegmentData(
 idx=r.idx,
 start=r.start,
 end=r.end,
 text=r.text,
 avg_logprob=r.avg_logprob,
 no_speech_prob=r.no_speech_prob,
 )
 for r in rows
 ]


def load_segments_with_meta(engine: Engine, job_id: str) -> list[dict]:
 with Session(engine) as s:
 rows = s.exec(
 select(Segment).where(Segment.job_id == job_id).order_by(Segment.idx)
 ).all()
 return [
 {
 "idx": r.idx,
 "start": r.start,
 "end": r.end,
 "text": r.text,
 "avg_logprob": r.avg_logprob,
 "no_speech_prob": r.no_speech_prob,
 "edited": r.edited,
 }
 for r in rows
 ]


def update_segment(
 engine: Engine,
 job_id: str,
 idx: int,
 text: str | None = None,
 start: float | None = None,
 end: float | None = None,
) -> bool:
 with Session(engine) as s:
 row = s.exec(
 select(Segment).where(Segment.job_id == job_id, Segment.idx == idx)
 ).first()
 if row is None:
 return False
 if text is not None:
 row.text = text
 if start is not None:
 row.start = start
 if end is not None:
 row.end = end
 row.edited = True
 s.add(row)
 s.commit()
 return True


def search_and_replace(
 engine: Engine,
 job_id: str,
 find: str,
 replace: str,
 case_sensitive: bool = False,
) -> int:
 if not find:
 return 0
 with Session(engine) as s:
 rows = s.exec(
 select(Segment).where(Segment.job_id == job_id).order_by(Segment.idx)
 ).all()
 count = 0
 for r in rows:
 if case_sensitive:
 if find in r.text:
 r.text = r.text.replace(find, replace)
 r.edited = True
 count += 1
 s.add(r)
 else:
 lower = r.text.lower()
 if find.lower() in lower:
 start_idx = lower.find(find.lower())
 while start_idx != -1:
 r.text = r.text[:start_idx] + replace + r.text[start_idx + len(find):]
 lower = r.text.lower()
 start_idx = lower.find(find.lower(), start_idx + len(replace))
 r.edited = True
 count += 1
 s.add(r)
 s.commit()
 return count
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_segments_service.py -v`
Expected: 3 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/segments.py backend/tests/test_segments_service.py
git commit -m "feat(backend): add segment CRUD + search/replace service"
```

---

### Task 3.3: yt-dlp 다운로더 래퍼

**Files:**
- Create: `backend/app/services/downloader.py`
- Create: `backend/tests/test_downloader.py`

- [ ] **Step 1: 진행률 계산 단위 테스트 (yt-dlp 자체는 모킹)**

Write `backend/tests/test_downloader.py`:

```python
from app.services.downloader import parse_progress_hook


def test_parse_progress_hook_downloading():
 info = {
 "status": "downloading",
 "downloaded_bytes": 512,
 "total_bytes": 2048,
 }
 pct = parse_progress_hook(info)
 assert pct == 0.25


def test_parse_progress_hook_fallback_total_bytes_estimate():
 info = {
 "status": "downloading",
 "downloaded_bytes": 100,
 "total_bytes_estimate": 400,
 }
 assert parse_progress_hook(info) == 0.25


def test_parse_progress_hook_finished():
 info = {"status": "finished"}
 assert parse_progress_hook(info) == 1.0


def test_parse_progress_hook_missing_info():
 assert parse_progress_hook({"status": "downloading"}) == 0.0
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_downloader.py -v`

- [ ] **Step 3: 다운로더 구현**

Write `backend/app/services/downloader.py`:

```python
from pathlib import Path
from typing import Any, Callable

import yt_dlp


def parse_progress_hook(info: dict[str, Any]) -> float:
 status = info.get("status")
 if status == "finished":
 return 1.0
 downloaded = info.get("downloaded_bytes") or 0
 total = info.get("total_bytes") or info.get("total_bytes_estimate") or 0
 if total <= 0:
 return 0.0
 return min(1.0, max(0.0, downloaded / total))


class DownloadResult:
 def __init__(self, path: Path, title: str | None, duration: float | None):
 self.path = path
 self.title = title
 self.duration = duration


def download_video(
 url: str,
 dest_dir: Path,
 progress_callback: Callable[[float], None] | None = None,
 cookies_file: Path | None = None,
) -> DownloadResult:
 """
 yt-dlp로 URL을 다운로드한다. dest_dir에 source.* 파일로 저장.
 """
 dest_dir.mkdir(parents=True, exist_ok=True)
 out_template = str(dest_dir / "source.%(ext)s")

 last_pct = [0.0]

 def hook(info: dict[str, Any]) -> None:
 pct = parse_progress_hook(info)
 if pct - last_pct[0] >= 0.01 or pct in (0.0, 1.0):
 last_pct[0] = pct
 if progress_callback:
 progress_callback(pct)

 ydl_opts: dict[str, Any] = {
 "format": "bv*+ba/b",
 "outtmpl": out_template,
 "progress_hooks": [hook],
 "merge_output_format": "mp4",
 "noprogress": True,
 "quiet": True,
 }
 if cookies_file and cookies_file.exists():
 ydl_opts["cookiefile"] = str(cookies_file)

 with yt_dlp.YoutubeDL(ydl_opts) as ydl:
 info = ydl.extract_info(url, download=True)

 downloaded = next(iter(dest_dir.glob("source.*")), None)
 if downloaded is None:
 raise RuntimeError("yt-dlp finished but no file found")

 return DownloadResult(
 path=downloaded,
 title=info.get("title"),
 duration=info.get("duration"),
 )
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_downloader.py -v`
Expected: 4 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/downloader.py backend/tests/test_downloader.py
git commit -m "feat(backend): add yt-dlp downloader wrapper"
```

---

### Task 3.4: ffmpeg 오디오 추출 래퍼

**Files:**
- Create: `backend/app/services/audio.py`
- Create: `backend/tests/test_audio.py`

- [ ] **Step 1: ffmpeg 명령어 빌더 단위 테스트**

Write `backend/tests/test_audio.py`:

```python
from pathlib import Path

from app.services.audio import build_extract_args


def test_build_extract_args_produces_16k_mono_wav():
 args = build_extract_args(Path("/in/src.mp4"), Path("/out/audio.wav"))
 assert "-i" in args
 assert "/in/src.mp4" in args
 assert "-ac" in args
 assert "1" in args
 assert "-ar" in args
 assert "16000" in args
 assert "/out/audio.wav" in args


def test_build_extract_args_overwrites():
 args = build_extract_args(Path("/in/a.mp4"), Path("/out/a.wav"))
 assert "-y" in args
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_audio.py -v`

- [ ] **Step 3: 오디오 추출 구현**

Write `backend/app/services/audio.py`:

```python
import subprocess
from pathlib import Path


def build_extract_args(source: Path, dest: Path) -> list[str]:
 return [
 "ffmpeg",
 "-y",
 "-i",
 str(source),
 "-vn",
 "-ac",
 "1",
 "-ar",
 "16000",
 "-f",
 "wav",
 str(dest),
 ]


def extract_audio(source: Path, dest: Path) -> Path:
 dest.parent.mkdir(parents=True, exist_ok=True)
 args = build_extract_args(source, dest)
 proc = subprocess.run(args, capture_output=True, text=True)
 if proc.returncode != 0:
 raise RuntimeError(f"ffmpeg extract failed: {proc.stderr[:500]}")
 return dest
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_audio.py -v`
Expected: 2 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/audio.py backend/tests/test_audio.py
git commit -m "feat(backend): add ffmpeg audio extraction wrapper"
```

---

### Task 3.5: faster-whisper 전사기 래퍼

**Files:**
- Create: `backend/app/services/transcriber.py`
- Create: `backend/tests/test_transcriber.py`

- [ ] **Step 1: 모델 로딩/결과 변환 단위 테스트 (실제 모델 로드 없이)**

Write `backend/tests/test_transcriber.py`:

```python
from app.services.transcriber import (
 TranscribeResult,
 segments_from_whisper_output,
)


class _FakeWord:
 def __init__(self, start, end, word):
 self.start = start
 self.end = end
 self.word = word


class _FakeSegment:
 def __init__(self, start, end, text, avg_logprob, no_speech_prob, words=None):
 self.start = start
 self.end = end
 self.text = text
 self.avg_logprob = avg_logprob
 self.no_speech_prob = no_speech_prob
 self.words = words


def test_segments_from_whisper_output_maps_fields():
 whisper_segs = [
 _FakeSegment(0.0, 2.5, " hi there ", -0.3, 0.01, [_FakeWord(0, 1, "hi"), _FakeWord(1, 2, "there")]),
 _FakeSegment(2.5, 4.0, " bye ", -0.4, 0.02, None),
 ]
 result = segments_from_whisper_output(whisper_segs)
 assert len(result) == 2
 assert result[0].idx == 0
 assert result[0].text == "hi there"
 assert result[0].avg_logprob == -0.3
 assert result[1].text == "bye"
 assert result[1].idx == 1
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_transcriber.py -v`

- [ ] **Step 3: 전사기 구현**

Write `backend/app/services/transcriber.py`:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from app.services.subtitles import SegmentData


@dataclass
class TranscribeResult:
 segments: list[SegmentData]
 language: str
 duration: float


def segments_from_whisper_output(whisper_segments: Iterable[Any]) -> list[SegmentData]:
 out: list[SegmentData] = []
 for i, seg in enumerate(whisper_segments):
 out.append(
 SegmentData(
 idx=i,
 start=float(seg.start),
 end=float(seg.end),
 text=seg.text.strip(),
 avg_logprob=getattr(seg, "avg_logprob", None),
 no_speech_prob=getattr(seg, "no_speech_prob", None),
 )
 )
 return out


def transcribe(
 audio_path: Path,
 model_name: str,
 compute_type: str,
 model_cache_dir: Path,
 language: str | None = None,
 initial_prompt: str | None = None,
 progress_callback: Callable[[float], None] | None = None,
) -> TranscribeResult:
 from faster_whisper import WhisperModel

 model = WhisperModel(
 model_name,
 device="cpu",
 compute_type=compute_type,
 download_root=str(model_cache_dir),
 )

 segments_iter, info = model.transcribe(
 str(audio_path),
 beam_size=5,
 vad_filter=True,
 word_timestamps=True,
 language=language,
 initial_prompt=initial_prompt,
 )

 total_duration = info.duration or 1.0
 collected: list[Any] = []
 for seg in segments_iter:
 collected.append(seg)
 if progress_callback and seg.end > 0:
 progress_callback(min(1.0, seg.end / total_duration))

 mapped = segments_from_whisper_output(collected)
 return TranscribeResult(
 segments=mapped,
 language=info.language,
 duration=float(info.duration or 0.0),
 )
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_transcriber.py -v`
Expected: 1 passed. (실제 모델 로드는 하지 않고 매핑 로직만 테스트.)

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/transcriber.py backend/tests/test_transcriber.py
git commit -m "feat(backend): add faster-whisper transcriber wrapper"
```

---

### Task 3.6: mkvmerge 먹스 래퍼

**Files:**
- Create: `backend/app/services/muxer.py`
- Create: `backend/tests/test_muxer.py`

- [ ] **Step 1: 명령어 빌더 테스트**

Write `backend/tests/test_muxer.py`:

```python
from pathlib import Path

from app.services.muxer import build_mkvmerge_args


def test_build_mkvmerge_args_includes_video_and_subtitle():
 args = build_mkvmerge_args(
 video=Path("/m/source.mp4"),
 subtitle=Path("/m/subtitles.srt"),
 output=Path("/m/video+subs.mkv"),
 language="ko",
 )
 assert args[0] == "mkvmerge"
 assert "-o" in args
 assert "/m/video+subs.mkv" in args
 assert "/m/source.mp4" in args
 assert "--language" in args
 assert "0:ko" in args
 assert "/m/subtitles.srt" in args
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_muxer.py -v`

- [ ] **Step 3: 먹서 구현**

Write `backend/app/services/muxer.py`:

```python
import subprocess
from pathlib import Path


def build_mkvmerge_args(
 video: Path,
 subtitle: Path,
 output: Path,
 language: str = "und",
) -> list[str]:
 return [
 "mkvmerge",
 "-o",
 str(output),
 str(video),
 "--language",
 f"0:{language}",
 str(subtitle),
 ]


def mux_video_with_subtitles(
 video: Path,
 subtitle: Path,
 output: Path,
 language: str = "und",
) -> Path:
 output.parent.mkdir(parents=True, exist_ok=True)
 args = build_mkvmerge_args(video, subtitle, output, language)
 proc = subprocess.run(args, capture_output=True, text=True)
 if proc.returncode != 0:
 raise RuntimeError(f"mkvmerge failed: {proc.stderr[:500]}")
 return output
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_muxer.py -v`
Expected: 1 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/muxer.py backend/tests/test_muxer.py
git commit -m "feat(backend): add mkvmerge subtitle muxer"
```

---

### Task 3.7: SRT → ASS 변환 (burn-in 스타일링)

**Files:**
- Create: `backend/app/services/ass_style.py`
- Create: `backend/tests/test_ass_style.py`

- [ ] **Step 1: ASS 생성 단위 테스트**

Write `backend/tests/test_ass_style.py`:

```python
from app.services.ass_style import BurnStyle, srt_segments_to_ass
from app.services.subtitles import SegmentData


def test_ass_contains_dialogue_and_style_header():
 segs = [
 SegmentData(idx=0, start=0.0, end=1.5, text="안녕"),
 SegmentData(idx=1, start=1.5, end=3.0, text="세상"),
 ]
 ass = srt_segments_to_ass(
 segs,
 BurnStyle(font="Pretendard", size=48, outline=True),
 )
 assert "[Script Info]" in ass
 assert "[V4+ Styles]" in ass
 assert "[Events]" in ass
 assert "Dialogue: 0,0:00:00.00,0:00:01.50,Default,,0,0,0,,안녕" in ass
 assert "Dialogue: 0,0:00:01.50,0:00:03.00,Default,,0,0,0,,세상" in ass
 assert "Pretendard" in ass


def test_burn_style_size_defaults():
 s = BurnStyle()
 assert s.font == "Pretendard"
 assert s.size == 42
 assert s.outline is True
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_ass_style.py -v`

- [ ] **Step 3: ASS 생성 구현**

Write `backend/app/services/ass_style.py`:

```python
from dataclasses import dataclass
from typing import Iterable

from app.services.subtitles import SegmentData


@dataclass
class BurnStyle:
 font: str = "Pretendard"
 size: int = 42
 outline: bool = True


def _ts_ass(t: float) -> str:
 h = int(t // 3600)
 m = int((t % 3600) // 60)
 s_int = int(t % 60)
 cs = int(round((t - int(t)) * 100))
 return f"{h}:{m:02d}:{s_int:02d}.{cs:02d}"


HEADER_TEMPLATE = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{outline_thickness},0,2,40,40,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def srt_segments_to_ass(segments: Iterable[SegmentData], style: BurnStyle) -> str:
 outline_thickness = 2 if style.outline else 0
 out = [
 HEADER_TEMPLATE.format(
 font=style.font,
 size=style.size,
 outline_thickness=outline_thickness,
 )
 ]
 for seg in segments:
 text = seg.text.replace("\n", "\\N")
 out.append(
 f"Dialogue: 0,{_ts_ass(seg.start)},{_ts_ass(seg.end)},Default,,0,0,0,,{text}"
 )
 return "\n".join(out)
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_ass_style.py -v`
Expected: 2 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/ass_style.py backend/tests/test_ass_style.py
git commit -m "feat(backend): add SRT-to-ASS converter with burn style"
```

---

### Task 3.8: ffmpeg burn-in 렌더러

**Files:**
- Create: `backend/app/services/burn.py`
- Create: `backend/tests/test_burn.py`

- [ ] **Step 1: 명령어 빌더 테스트**

Write `backend/tests/test_burn.py`:

```python
from pathlib import Path

from app.services.burn import build_burn_args


def test_build_burn_args_video_filter_uses_ass():
 args = build_burn_args(
 video=Path("/b/source.mp4"),
 ass=Path("/b/subtitles.ass"),
 output=Path("/b/burned.mp4"),
 )
 assert args[0] == "ffmpeg"
 assert "-y" in args
 assert "/b/source.mp4" in args
 vf_idx = args.index("-vf")
 assert "ass=/b/subtitles.ass" in args[vf_idx + 1]
 assert "/b/burned.mp4" in args
 assert "-c:a" in args
 assert "copy" in args
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_burn.py -v`

- [ ] **Step 3: burn 구현**

Write `backend/app/services/burn.py`:

```python
import re
import subprocess
from pathlib import Path
from typing import Callable


def build_burn_args(video: Path, ass: Path, output: Path) -> list[str]:
 return [
 "ffmpeg",
 "-y",
 "-i",
 str(video),
 "-vf",
 f"ass={ass}",
 "-c:a",
 "copy",
 "-c:v",
 "libx264",
 "-preset",
 "medium",
 "-crf",
 "23",
 "-progress",
 "pipe:1",
 "-nostats",
 str(output),
 ]


_TIME_RE = re.compile(r"out_time_ms=(\d+)")


def burn_video(
 video: Path,
 ass: Path,
 output: Path,
 total_duration_sec: float,
 progress_callback: Callable[[float], None] | None = None,
) -> Path:
 output.parent.mkdir(parents=True, exist_ok=True)
 args = build_burn_args(video, ass, output)
 proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
 assert proc.stdout is not None
 total_us = total_duration_sec * 1_000_000
 for raw in proc.stdout:
 m = _TIME_RE.search(raw)
 if m and total_us > 0 and progress_callback:
 processed = int(m.group(1))
 progress_callback(min(1.0, processed / total_us))
 rc = proc.wait()
 if rc != 0:
 err = proc.stderr.read() if proc.stderr else ""
 raise RuntimeError(f"burn failed: {err[:500]}")
 return output
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_burn.py -v`
Expected: 1 passed.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add backend/app/services/burn.py backend/tests/test_burn.py
git commit -m "feat(backend): add ffmpeg burn-in renderer with progress parsing"
```

---

