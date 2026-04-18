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
