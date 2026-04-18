import subprocess
from pathlib import Path

from app.services.ass_style import BurnStyle, srt_segments_to_ass
from app.services.subtitles import SegmentData


def build_clip_args(
    video: Path,
    output: Path,
    start: float,
    end: float,
    ass: Path | None = None,
) -> list[str]:
    args = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-to",
        str(end),
        "-i",
        str(video),
    ]
    if ass:
        args.extend(["-vf", f"ass={ass}"])
        args.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "23"])
    else:
        args.extend(["-c:v", "copy"])
    args.extend(["-c:a", "copy", str(output)])
    return args


def export_clip(
    video: Path,
    output: Path,
    start: float,
    end: float,
    segments: list[SegmentData] | None = None,
    style: BurnStyle | None = None,
) -> Path:
    """Export a time-range clip, optionally with burned-in subtitles."""
    output.parent.mkdir(parents=True, exist_ok=True)

    ass_path: Path | None = None
    if segments:
        # Filter segments that overlap with the clip range
        clipped = [
            SegmentData(
                idx=i,
                start=max(0.0, s.start - start),
                end=min(end - start, s.end - start),
                text=s.text,
                avg_logprob=s.avg_logprob,
                no_speech_prob=s.no_speech_prob,
            )
            for i, s in enumerate(segments)
            if s.end > start and s.start < end
        ]
        if clipped:
            ass_path = output.parent / f"clip-{start:.1f}-{end:.1f}.ass"
            ass_path.write_text(
                srt_segments_to_ass(clipped, style or BurnStyle()),
                encoding="utf-8",
            )

    args = build_clip_args(video, output, start, end, ass_path)
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"clip export failed: {proc.stderr[:500]}")

    # Clean up temp ASS file
    if ass_path and ass_path.exists():
        ass_path.unlink(missing_ok=True)

    return output
