from app.services.subtitles import (
    SegmentData,
    format_json,
    format_srt,
    format_txt,
    format_vtt,
)

SEGMENTS = [
    SegmentData(idx=0, start=0.0, end=3.5, text="안녕하세요"),
    SegmentData(idx=1, start=3.5, end=7.25, text="반갑습니다"),
]


def test_format_srt():
    out = format_srt(SEGMENTS)
    assert "1\n00:00:00,000 --> 00:00:03,500\n안녕하세요" in out
    assert "2\n00:00:03,500 --> 00:00:07,250\n반갑습니다" in out


def test_format_vtt():
    out = format_vtt(SEGMENTS)
    assert out.startswith("WEBVTT\n")
    assert "00:00:00.000 --> 00:00:03.500" in out
    assert "안녕하세요" in out


def test_format_txt_is_plain_lines():
    out = format_txt(SEGMENTS)
    assert out == "안녕하세요\n반갑습니다\n"


def test_format_json_contains_timestamps():
    import json as _json
    out = format_json(SEGMENTS)
    data = _json.loads(out)
    assert data["segments"][0]["start"] == 0.0
    assert data["segments"][1]["text"] == "반갑습니다"
