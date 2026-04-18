from app.core.settings import Settings


def test_settings_defaults(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    s = Settings()
    assert s.gensub_role in ("api", "worker")
    assert s.job_ttl_hours == 24
    assert s.max_video_minutes == 90
    assert s.default_model == "small"
    assert s.compute_type == "int8"
    assert s.worker_concurrency == 1


def test_settings_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("JOB_TTL_HOURS", "48")
    monkeypatch.setenv("DEFAULT_MODEL", "medium")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path / "models"))
    s = Settings()
    assert s.job_ttl_hours == 48
    assert s.default_model == "medium"
