from app.services.subtitles import (
    SegmentData,
    _ts_srt,
    _ts_vtt,
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


def test_ts_srt_rollover_at_fractional_boundary():
    # 3.9999s is ~4000ms; must carry, not produce 03,1000
    assert _ts_srt(3.9999) == "00:00:04,000"


def test_ts_vtt_rollover_at_fractional_boundary():
    assert _ts_vtt(3.9999) == "00:00:04.000"


def test_ts_srt_exact_second():
    assert _ts_srt(1.0) == "00:00:01,000"


def test_ts_srt_hour_minute_second():
    assert _ts_srt(3723.456) == "01:02:03,456"
