from pathlib import Path

from app.services.audio import build_extract_args


def test_build_extract_args_produces_16k_mono_wav():
    args = build_extract_args(Path("/in/src.mp4"), Path("/out/audio.wav"))
    assert "-i" in args
    assert "/in/src.mp4" in args
    assert "-ac" in args
    assert "1" in args
    assert "-ar" in args
    assert "16000" in args
    assert "/out/audio.wav" in args


def test_build_extract_args_overwrites():
    args = build_extract_args(Path("/in/a.mp4"), Path("/out/a.wav"))
    assert "-y" in args
