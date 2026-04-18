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
