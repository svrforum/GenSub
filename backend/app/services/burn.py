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
    cancel_check: Callable[[], None] | None = None,
) -> Path:
    """ffmpeg burn-in. cancel_check가 예외를 raise하면 ffmpeg 종료 후 예외 재발생.

    Args:
        cancel_check: 진행률 루프 매 라인에 호출. 예외를 발생시키면 ffmpeg를
            terminate → wait(5s) → kill 순으로 정리한 뒤 같은 예외를 다시 raise.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    args = build_burn_args(video, ass, output)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.stdout is None:
        raise RuntimeError("ffmpeg process failed to start (stdout is None)")

    total_us = total_duration_sec * 1_000_000
    cancelled_exc: BaseException | None = None

    try:
        for raw in proc.stdout:
            if cancel_check is not None:
                try:
                    cancel_check()
                except BaseException as exc:  # JobCancelledError 등
                    cancelled_exc = exc
                    break
            m = _TIME_RE.search(raw)
            if m and total_us > 0 and progress_callback:
                processed = int(m.group(1))
                progress_callback(min(1.0, processed / total_us))
    finally:
        if cancelled_exc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

    if cancelled_exc is not None:
        raise cancelled_exc

    rc = proc.wait()
    if rc != 0:
        err = proc.stderr.read() if proc.stderr else ""
        raise RuntimeError(f"burn failed: {err[:500]}")
    return output
