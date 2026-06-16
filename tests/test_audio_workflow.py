import pytest
from unittest.mock import patch, MagicMock
import os, sys

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token")
os.environ.setdefault("OPENAI_API_KEY", "test_key")
os.environ.setdefault("DEEPSEEK_API_KEY", "test_key")
os.environ.setdefault("NOTION_TOKEN", "test_token")
os.environ.setdefault("NOTION_PAGE_ID", "test_page_id")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audio_workflow import app, transcribe_audio, summarize_text, save_to_notion


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_webhook_missing_voice(client):
    resp = client.post("/webhook", json={"message": {"text": "hello"}})
    assert resp.status_code == 200


def test_webhook_empty_body(client):
    resp = client.post("/webhook", json={})
    assert resp.status_code == 200


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


@patch("audio_workflow.requests.post")
def test_save_to_notion(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    save_to_notion("transcript", "summary", "file_id_123")
    mock_post.assert_called_once()
    args = mock_post.call_args
    assert "notion.com" in args[0][0]
