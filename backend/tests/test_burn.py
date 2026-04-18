from pathlib import Path

from app.services.burn import build_burn_args


def test_build_burn_args_video_filter_uses_ass():
    args = build_burn_args(
        video=Path("/b/source.mp4"),
        ass=Path("/b/subtitles.ass"),
        output=Path("/b/burned.mp4"),
    )
    assert args[0] == "ffmpeg"
    assert "-y" in args
    assert "/b/source.mp4" in args
    vf_idx = args.index("-vf")
    assert "ass=/b/subtitles.ass" in args[vf_idx + 1]
    assert "/b/burned.mp4" in args
    assert "-c:a" in args
    assert "copy" in args
