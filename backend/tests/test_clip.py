from pathlib import Path

from app.services.clip import build_clip_args


def test_build_clip_args_without_subtitles():
    args = build_clip_args(
        video=Path("/v/source.mp4"),
        output=Path("/v/clip.mp4"),
        start=10.0,
        end=20.0,
    )
    assert args[0] == "ffmpeg"
    assert "-ss" in args
    assert "10.0" in args
    assert "-to" in args
    assert "20.0" in args
    assert "-c:v" in args
    assert "copy" in args[args.index("-c:v") + 1]


def test_build_clip_args_with_subtitles():
    args = build_clip_args(
        video=Path("/v/source.mp4"),
        output=Path("/v/clip.mp4"),
        start=5.0,
        end=15.0,
        ass=Path("/v/clip.ass"),
    )
    assert "-vf" in args
    vf_idx = args.index("-vf")
    assert "ass=/v/clip.ass" in args[vf_idx + 1]
    assert "libx264" in args
