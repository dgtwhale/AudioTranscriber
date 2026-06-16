import pytest
from unittest.mock import patch, MagicMock
import os, sys

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token")
os.environ.setdefault("OPENAI_API_KEY", "test_key")
os.environ.setdefault("DEEPSEEK_API_KEY", "test_key")
os.environ.setdefault("NOTION_TOKEN", "test_token")
os.environ.setdefault("NOTION_PAGE_ID", "test_page_id")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audio_workflow import transcribe_audio, summarize_text, save_to_notion


@patch("audio_workflow.requests.post")
def test_transcribe_audio(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "тестовая транскрипция"}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = transcribe_audio(b"fake_audio_data")
    assert result == "тестовая транскрипция"
    mock_post.assert_called_once()


@patch("audio_workflow.requests.post")
def test_summarize_text(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "краткое содержание"}}]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = summarize_text("длинный текст для суммаризации")
    assert result == "краткое содержание"


@patch("audio_workflow.requests.patch")
@patch("audio_workflow.requests.post")
def test_save_to_notion(mock_post, mock_patch):
    page_response = MagicMock()
    page_response.json.return_value = {"id": "fake-page-id-123"}
    page_response.raise_for_status.return_value = None
    mock_post.return_value = page_response

    blocks_response = MagicMock()
    blocks_response.raise_for_status.return_value = None
    mock_patch.return_value = blocks_response

    result = save_to_notion("transcript text", "summary text", "file_id_123")
    assert result == "fake-page-id-123"
    mock_post.assert_called_once()
    mock_patch.assert_called_once()
    assert "notion.com" in mock_post.call_args[0][0]


def test_env_vars_loaded():
    import audio_workflow as aw
    assert aw.TELEGRAM_BOT_TOKEN is not None
    assert aw.OPENAI_API_KEY is not None
