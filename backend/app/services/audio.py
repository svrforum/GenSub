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
