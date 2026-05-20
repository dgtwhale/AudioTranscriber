#!/usr/bin/env python3
"""
Audio Transcriber with AI Summarization
Automatic voice transcription, AI summarization, and note-taking in Notion.
"""

import os
import logging
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_PAGE_ID')
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))

# API Endpoints
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
OPENAI_API = "https://api.openai.com/v1/audio/transcriptions"
DEEPSEEK_API = "https://api.deepseek.com/chat/completions"
NOTION_API = "https://api.notion.com/v1"


def get_file_from_telegram(file_id):
    """Download audio file from Telegram"""
    try:
        logger.info(f"Downloading file from Telegram: {file_id}")

        # Get file path
        response = requests.get(
            f"{TELEGRAM_API}/getFile",
            params={"file_id": file_id}
        )
        response.raise_for_status()
        file_path = response.json()['result']['file_path']

        # Download file
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        audio_response = requests.get(file_url)
        audio_response.raise_for_status()

        logger.info(f"Downloaded {len(audio_response.content)} bytes from Telegram")
        return audio_response.content
    except Exception as e:
        logger.error(f"Error downloading from Telegram: {str(e)}")
        raise


def transcribe_audio(audio_data, language='ru'):
    """Transcribe audio using OpenAI Whisper API"""
    try:
        logger.info("Starting transcription with Whisper API")

        files = {'file': ('audio.ogg', audio_data, 'audio/ogg')}
        data = {
            'model': 'whisper-1',
            'language': language
        }
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}'
        }

        response = requests.post(OPENAI_API, files=files, data=data, headers=headers)
        response.raise_for_status()

        transcript = response.json()['text']
        logger.info(f"Transcription done: {transcript[:100]}...")
        return transcript
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        raise


def summarize_text(text, language='Russian'):
    """Summarize text using DeepSeek API"""
    try:
        logger.info("Starting summarization with DeepSeek API")

        prompt = f"""Summarize the following text in {language} language.
        Keep it concise (2-3 sentences max).

        Text: {text}

        Summary:"""

        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': 'deepseek-chat',
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': 500
        }

        response = requests.post(DEEPSEEK_API, json=payload, headers=headers)
        response.raise_for_status()

        summary = response.json()['choices'][0]['message']['content']
        logger.info(f"Summary done: {summary[:100]}...")
        return summary
    except Exception as e:
        logger.error(f"Error summarizing text: {str(e)}")
        raise


def save_to_notion(transcript, summary, file_id):
    """Save transcript and summary to Notion database"""
    try:
        logger.info("Saving to Notion database")

        headers = {
            'Authorization': f'Bearer {NOTION_TOKEN}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }

        # Create page with title
        page_data = {
            'parent': {'database_id': NOTION_DATABASE_ID},
            'properties': {
                'Title': {
                    'title': [
                        {
                            'text': {
                                'content': f'Audio {file_id[:8]}...'
                            }
                        }
                    ]
                },
                'File ID': {
                    'rich_text': [
                        {
                            'text': {
                                'content': file_id
                            }
                        }
                    ]
                },
                'Created Date': {
                    'date': {
                        'start': datetime.now().isoformat()
                    }
                }
            }
        }

        # Create page
        create_response = requests.post(
            f'{NOTION_API}/pages',
            json=page_data,
            headers=headers
        )
        create_response.raise_for_status()
        page_id = create_response.json()['id']
        logger.info(f"Created Notion page: {page_id}")

        # Add content blocks (transcription and summary)
        blocks_data = {
            'children': [
                {
                    'object': 'block',
                    'type': 'heading_2',
                    'heading_2': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {
                                    'content': 'Transcription'
                                }
                            }
                        ]
                    }
                },
                {
                    'object': 'block',
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {
                                    'content': transcript
                                }
                            }
                        ]
                    }
                },
                {
                    'object': 'block',
                    'type': 'heading_2',
                    'heading_2': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {
                                    'content': 'Summary'
                                }
                            }
                        ]
                    }
                },
                {
                    'object': 'block',
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {
                                    'content': summary
                                }
                            }
                        ]
                    }
                }
            ]
        }

        # Add blocks to page
        blocks_response = requests.patch(
            f'{NOTION_API}/blocks/{page_id}/children',
            json=blocks_data,
            headers=headers
        )
        blocks_response.raise_for_status()
        logger.info(f"Successfully saved to Notion")

        return page_id
    except Exception as e:
        logger.error(f"Error saving to Notion: {str(e)}")
        raise


@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint"""
    try:
        update = request.json
        logger.info(f"Received webhook update")

        # Check if message contains voice/audio
        if 'message' in update and 'voice' in update['message']:
            voice = update['message']['voice']
            file_id = voice['file_id']

            # Process audio
            audio_data = get_file_from_telegram(file_id)
            transcript = transcribe_audio(audio_data)
            summary = summarize_text(transcript)
            save_to_notion(transcript, summary, file_id)

            logger.info("Successfully processed voice message")
            return jsonify({'ok': True, 'message': 'Processed successfully'})

        elif 'message' in update and 'audio' in update['message']:
            audio = update['message']['audio']
            file_id = audio['file_id']

            # Process audio
            audio_data = get_file_from_telegram(file_id)
            transcript = transcribe_audio(audio_data)
            summary = summarize_text(transcript)
            save_to_notion(transcript, summary, file_id)

            logger.info("Successfully processed audio message")
            return jsonify({'ok': True, 'message': 'Processed successfully'})

        return jsonify({'ok': True, 'message': 'Skipped'})

    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    logger.info(f"Starting Flask app on port {FLASK_PORT}")
    app.run(host='0.0.0.0', port=FLASK_PORT, debug=False)
