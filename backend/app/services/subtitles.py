import json
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass
class SegmentData:
    idx: int
    start: float
    end: float
    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None


def _ts_srt(t: float) -> str:
    total_ms = int(round(t * 1000))
    if total_ms < 0:
        total_ms = 0
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _ts_vtt(t: float) -> str:
    total_ms = int(round(t * 1000))
    if total_ms < 0:
        total_ms = 0
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def format_srt(segments: Iterable[SegmentData]) -> str:
    lines = []
    for seg in segments:
        lines.append(str(seg.idx + 1))
        lines.append(f"{_ts_srt(seg.start)} --> {_ts_srt(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)


def format_vtt(segments: Iterable[SegmentData]) -> str:
    lines = ["WEBVTT", ""]
    # cue 설정 (긴 자막의 wrap 잘림 방지):
    # - size:90%        영상 가로폭의 90%까지 사용 → 한 줄에 더 많이 담아 wrap 횟수 줄임
    # - position:50% align:center  가로 중앙 정렬
    # - line: 명시 안 함 → 브라우저 기본(line:auto, 정수 line-snap)
    #   wrap된 cue 가 화면 바닥부터 채워지며 자동으로 위로 push → 잘림 방지
    cue_settings = "size:90% align:center position:50%"
    for seg in segments:
        lines.append(f"{_ts_vtt(seg.start)} --> {_ts_vtt(seg.end)} {cue_settings}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)


def format_txt(segments: Iterable[SegmentData]) -> str:
    return "".join(seg.text + "\n" for seg in segments)


def format_json(segments: Iterable[SegmentData]) -> str:
    data = {
        "segments": [
            {
                "idx": s.idx,
                "start": s.start,
                "end": s.end,
                "text": s.text,
                "avg_logprob": s.avg_logprob,
                "no_speech_prob": s.no_speech_prob,
            }
            for s in segments
        ]
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
