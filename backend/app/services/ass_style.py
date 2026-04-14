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


_V4_FORMAT_FIELDS = (
    "Name",
    "Fontname",
    "Fontsize",
    "PrimaryColour",
    "SecondaryColour",
    "OutlineColour",
    "BackColour",
    "Bold",
    "Italic",
    "Underline",
    "StrikeOut",
    "ScaleX",
    "ScaleY",
    "Spacing",
    "Angle",
    "BorderStyle",
    "Outline",
    "Shadow",
    "Alignment",
    "MarginL",
    "MarginR",
    "MarginV",
    "Encoding",
)

_V4_FORMAT_LINE = "Format: " + ", ".join(_V4_FORMAT_FIELDS)

_STYLE_DEFAULT_LINE = (
    "Style: Default,{font},{size},"
    "&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
    "0,0,0,0,100,100,0,0,1,{outline_thickness},0,2,40,40,40,1"
)

HEADER_TEMPLATE = (
    "[Script Info]\n"
    "ScriptType: v4.00+\n"
    "PlayResX: 1920\n"
    "PlayResY: 1080\n"
    "WrapStyle: 0\n"
    "ScaledBorderAndShadow: yes\n"
    "\n"
    "[V4+ Styles]\n"
    f"{_V4_FORMAT_LINE}\n"
    f"{_STYLE_DEFAULT_LINE}\n"
    "\n"
    "[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
)


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
