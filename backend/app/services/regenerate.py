import subprocess
from pathlib import Path

from sqlalchemy.engine import Engine

from app.core.settings import Settings
from app.models.job import Job
from app.services.audio import extract_audio
from app.services.segments import load_segments, replace_all_segments
from app.services.subtitles import SegmentData
from app.services.transcriber import transcribe

PADDING_SEC = 2.0


def _slice_audio(source_wav: Path, dest_wav: Path, start: float, end: float) -> Path:
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source_wav),
            "-ss",
            str(start),
            "-to",
            str(end),
            "-c",
            "copy",
            str(dest_wav),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"slice failed: {proc.stderr[:500]}")
    return dest_wav


def regenerate_segment(
    settings: Settings,
    engine: Engine,
    job: Job,
    idx: int,
) -> None:
    segments = load_segments(engine, job.id)
    target = next((s for s in segments if s.idx == idx), None)
    if target is None:
        raise RuntimeError("segment not found")

    media_dir = settings.media_dir / job.id
    audio_path = media_dir / "audio.wav"
    if not audio_path.exists():
        source = next(iter(media_dir.glob("source.*")), None)
        if source is None:
            raise RuntimeError("source missing")
        audio_path = extract_audio(source, audio_path)

    slice_start = max(0.0, target.start - PADDING_SEC)
    slice_end = target.end + PADDING_SEC
    slice_path = media_dir / f"slice-{idx}.wav"
    _slice_audio(audio_path, slice_path, slice_start, slice_end)

    result = transcribe(
        audio_path=slice_path,
        model_name=job.model_name,
        compute_type=settings.compute_type,
        model_cache_dir=settings.model_cache_dir,
        language=job.language,
        initial_prompt=job.initial_prompt,
    )
    slice_path.unlink(missing_ok=True)

    # Retranscription result uses slice-relative timestamps — adjust to absolute
    adjusted = [
        SegmentData(
            idx=0,
            start=s.start + slice_start,
            end=s.end + slice_start,
            text=s.text,
            avg_logprob=s.avg_logprob,
            no_speech_prob=s.no_speech_prob,
        )
        for s in result.segments
    ]

    # Replace target segment with adjusted segments, keep rest unchanged
    new_segments: list[SegmentData] = []
    for s in segments:
        if s.idx == idx:
            new_segments.extend(adjusted)
        else:
            new_segments.append(s)

    # Renumber idx sequentially (SegmentData is a mutable dataclass)
    for i, s in enumerate(new_segments):
        s.idx = i

    replace_all_segments(engine, job.id, new_segments)
