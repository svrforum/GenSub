import pytest

from app.services.downloader import download_video, parse_progress_hook


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


def test_download_video_raises_when_cookies_file_missing(tmp_path):
    missing = tmp_path / "nope.txt"
    with pytest.raises(FileNotFoundError, match="cookies_file not found"):
        download_video(
            url="https://example.com/ignored",
            dest_dir=tmp_path / "dl",
            cookies_file=missing,
        )
