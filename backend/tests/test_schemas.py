import pytest
from pydantic import ValidationError

from app.api.schemas import JobCreateRequest


def test_job_create_requires_url_or_upload_kind():
    req = JobCreateRequest(url="https://youtu.be/abc", model="small")
    assert req.url == "https://youtu.be/abc"
    assert req.model == "small"
    assert req.language is None


def test_job_create_rejects_unknown_model():
    with pytest.raises(ValidationError):
        JobCreateRequest(url="https://youtu.be/abc", model="gigantic")


def test_job_create_accepts_initial_prompt():
    req = JobCreateRequest(
        url="https://youtu.be/abc", model="small", initial_prompt="transformer attention"
    )
    assert req.initial_prompt == "transformer attention"
