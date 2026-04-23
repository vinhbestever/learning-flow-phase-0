import pytest

from agents.model_config import get_provider, is_allowed


def test_gpt_4_1_allowed() -> None:
    assert is_allowed("gpt-4.1") is True
    assert get_provider("gpt-4.1") == "openai"


def test_gemini_flash_allowed() -> None:
    assert is_allowed("gemini-2.0-flash") is True
    assert get_provider("gemini-2.0-flash") == "google"


def test_unknown_rejected() -> None:
    assert is_allowed("gpt-5-fake") is False


def test_get_provider_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown or disallowed"):
        get_provider("not-a-model")
