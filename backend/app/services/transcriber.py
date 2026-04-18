from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


CANCEL_CHECK_INTERVAL = 5  # check cancel every N segments


def transcribe(
    audio_path: Path,
    model_name: str,
    compute_type: str,
    model_cache_dir: Path,
    language: str | None = None,
    initial_prompt: str | None = None,
    progress_callback: Callable[[float], None] | None = None,
    cancel_check: Callable[[], None] | None = None,
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
        if cancel_check and len(collected) % CANCEL_CHECK_INTERVAL == 0:
            cancel_check()

    mapped = segments_from_whisper_output(collected)
    return TranscribeResult(
        segments=mapped,
        language=info.language,
        duration=float(info.duration or 0.0),
    )
