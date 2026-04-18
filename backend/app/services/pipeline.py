from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.core.settings import Settings
from app.models.job import Job, JobStatus
from app.services import job_state
from app.services.ass_style import BurnStyle, srt_segments_to_ass
from app.services.audio import extract_audio
from app.services.burn import burn_video
from app.services.downloader import download_video
from app.services.segments import load_segments, replace_all_segments
from app.services.subtitles import SegmentData, format_srt, format_vtt
from app.services.transcriber import transcribe


class JobCancelledError(Exception):
    pass


def _check_cancel(engine: Engine, job_id: str) -> None:
    if job_state.is_cancel_requested(engine, job_id):
        raise JobCancelledError(job_id)


def _write_subtitle_files(media_dir: Path, segments: list[SegmentData]) -> None:
    (media_dir / "subtitles.srt").write_text(format_srt(segments), encoding="utf-8")
    (media_dir / "subtitles.vtt").write_text(format_vtt(segments), encoding="utf-8")


def process_job(settings: Settings, engine: Engine, job_id: str) -> None:
    media_dir = settings.media_dir / job_id
    media_dir.mkdir(parents=True, exist_ok=True)

    try:
        # --- 1. 다운로드 ---
        job_state.update_progress(engine, job_id, 0.0, "영상을 가져오고 있어요")

        def dl_progress(pct: float) -> None:
            job_state.update_progress(engine, job_id, pct)

        with Session(engine) as s:
            job = s.get(Job, job_id)
            if job is None:
                return
            source_kind = job.source_kind
            source_url = job.source_url
            model_name = job.model_name
            language_override = job.language
            initial_prompt = job.initial_prompt

        if source_kind == "url":
            if not source_url:
                raise RuntimeError("url missing")
            result = download_video(
                url=source_url, dest_dir=media_dir, progress_callback=dl_progress
            )
            job_state.update_title_and_duration(
                engine, job_id, result.title, result.duration
            )
            source_path = result.path
        else:
            candidates = list(media_dir.glob("source.*"))
            if not candidates:
                raise RuntimeError("uploaded source file missing")
            source_path = candidates[0]

        _check_cancel(engine, job_id)

        # --- 2. 음성 추출 ---
        job_state.update_status(engine, job_id, JobStatus.transcribing, "음성을 듣고 있어요")
        audio_path = extract_audio(source_path, media_dir / "audio.wav")

        _check_cancel(engine, job_id)

        # --- 3. 전사 ---
        def tr_progress(pct: float) -> None:
            job_state.update_progress(engine, job_id, pct)

        def tr_cancel_check() -> None:
            _check_cancel(engine, job_id)

        # 한영 혼합 모드: language=None으로 auto-detect하되
        # initial_prompt에 양쪽 언어 힌트를 넣어 code-switch 인식 개선
        tr_language = language_override
        tr_prompt = initial_prompt
        if language_override and "+" in language_override:
            tr_language = None  # auto-detect로 전환
            langs = language_override.split("+")
            hints = {
                "ko": "안녕하세요. 이것은 한국어와 English가 섞인 영상입니다.",
                "en": "Hello. This video contains both English and 한국어.",
                "ja": "こんにちは。この動画には日本語とEnglishが含まれています。",
                "zh": "你好。这个视频包含中文和English。",
            }
            prompt_parts = [hints.get(lang, "") for lang in langs]
            mixed_hint = " ".join(p for p in prompt_parts if p)
            tr_prompt = f"{mixed_hint} {initial_prompt or ''}".strip() or None

        tr_result = transcribe(
            audio_path=audio_path,
            model_name=model_name,
            compute_type=settings.compute_type,
            model_cache_dir=settings.model_cache_dir,
            language=tr_language,
            initial_prompt=tr_prompt,
            progress_callback=tr_progress,
            cancel_check=tr_cancel_check,
        )
        job_state.update_language(engine, job_id, tr_result.language)

        _check_cancel(engine, job_id)

        # --- 4. 저장 + ready ---
        replace_all_segments(engine, job_id, tr_result.segments)
        _write_subtitle_files(media_dir, tr_result.segments)
        job_state.mark_ready(engine, job_id)

    except JobCancelledError:
        job_state.mark_failed(engine, job_id, "사용자가 작업을 취소했어요")
    except Exception as exc:
        job_state.mark_failed(engine, job_id, str(exc))


def process_burn_job(
    settings: Settings,
    engine: Engine,
    job_id: str,
    style: BurnStyle | None = None,
) -> None:
    media_dir = settings.media_dir / job_id

    def _cancel() -> None:
        _check_cancel(engine, job_id)

    try:
        _cancel()  # 시작 전 체크

        with Session(engine) as s:
            job = s.get(Job, job_id)
            if job is None:
                return
            duration = job.duration_sec or 1.0

        source_candidates = list(media_dir.glob("source.*"))
        if not source_candidates:
            raise RuntimeError("source video missing")
        source = source_candidates[0]

        segments = load_segments(engine, job_id)
        ass_path = media_dir / "subtitles.ass"
        ass_path.write_text(
            srt_segments_to_ass(segments, style or BurnStyle()),
            encoding="utf-8",
        )

        job_state.update_progress(engine, job_id, 0.0, "자막을 영상에 입히고 있어요")

        def burn_progress(pct: float) -> None:
            job_state.update_progress(engine, job_id, pct)

        output = media_dir / "burned.mp4"
        burn_video(
            video=source,
            ass=ass_path,
            output=output,
            total_duration_sec=duration,
            progress_callback=burn_progress,
            cancel_check=_cancel,
        )
        _cancel()  # 완료 직전 최종 체크
        job_state.mark_done(engine, job_id)
    except JobCancelledError:
        # 부분 생성된 burned.mp4 정리
        partial = media_dir / "burned.mp4"
        if partial.exists():
            partial.unlink(missing_ok=True)
        job_state.mark_failed(engine, job_id, "사용자가 작업을 취소했어요")
    except Exception as exc:
        job_state.mark_failed(engine, job_id, str(exc))
