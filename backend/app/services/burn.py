import re
import subprocess
from collections.abc import Callable
from pathlib import Path


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
    if proc.stdout is None:
        raise RuntimeError("ffmpeg process failed to start (stdout is None)")
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
