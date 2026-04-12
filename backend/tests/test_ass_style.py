from app.services.ass_style import BurnStyle, _ts_ass, srt_segments_to_ass
from app.services.subtitles import SegmentData


def test_ass_contains_dialogue_and_style_header():
    segs = [
        SegmentData(idx=0, start=0.0, end=1.5, text="안녕"),
        SegmentData(idx=1, start=1.5, end=3.0, text="세상"),
    ]
    ass = srt_segments_to_ass(
        segs,
        BurnStyle(font="Pretendard", size=48, outline=True),
    )
    assert "[Script Info]" in ass
    assert "[V4+ Styles]" in ass
    assert "[Events]" in ass
    assert "Dialogue: 0,0:00:00.00,0:00:01.50,Default,,0,0,0,,안녕" in ass
    assert "Dialogue: 0,0:00:01.50,0:00:03.00,Default,,0,0,0,,세상" in ass
    assert "Pretendard" in ass


def test_burn_style_size_defaults():
    s = BurnStyle()
    assert s.font == "Pretendard"
    assert s.size == 42
    assert s.outline is True


def test_ts_ass_rollover_at_fractional_boundary():
    # 3.9999s is ~400cs; must carry to 0:00:04.00, not produce 0:00:03.100
    assert _ts_ass(3.9999) == "0:00:04.00"


def test_ts_ass_hour_minute_second():
    assert _ts_ass(3723.45) == "1:02:03.45"
