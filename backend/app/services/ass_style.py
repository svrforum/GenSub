from collections.abc import Iterable
from dataclasses import dataclass

from app.services.subtitles import SegmentData


@dataclass
class BurnStyle:
    font: str = "Pretendard"
    size: int = 42
    outline: bool = True


def _ts_ass(t: float) -> str:
    total_cs = int(round(t * 100))
    if total_cs < 0:
        total_cs = 0
    h, rem = divmod(total_cs, 360_000)  # 3600 * 100
    m, rem = divmod(rem, 6000)           # 60 * 100
    s_int, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s_int:02d}.{cs:02d}"


HEADER_TEMPLATE = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{outline_thickness},0,2,40,40,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def srt_segments_to_ass(segments: Iterable[SegmentData], style: BurnStyle) -> str:
    outline_thickness = 2 if style.outline else 0
    out = [
        HEADER_TEMPLATE.format(
            font=style.font,
            size=style.size,
            outline_thickness=outline_thickness,
        )
    ]
    for seg in segments:
        text = seg.text.replace("\n", "\\N")
        out.append(
            f"Dialogue: 0,{_ts_ass(seg.start)},{_ts_ass(seg.end)},Default,,0,0,0,,{text}"
        )
    return "\n".join(out)
