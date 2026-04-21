import pytest
from pydantic import ValidationError

from app.api.schemas import MemoPatchRequest


def test_memo_patch_accepts_empty_string():
    req = MemoPatchRequest(memo_text="")
    assert req.memo_text == ""


def test_memo_patch_accepts_500_chars():
    req = MemoPatchRequest(memo_text="x" * 500)
    assert len(req.memo_text) == 500


def test_memo_patch_rejects_over_500_chars():
    with pytest.raises(ValidationError):
        MemoPatchRequest(memo_text="x" * 501)


def test_memo_patch_rejects_missing_field():
    with pytest.raises(ValidationError):
        MemoPatchRequest()
