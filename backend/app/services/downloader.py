from collections.abc import Callable
from pathlib import Path
from typing import Any

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
