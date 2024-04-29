import os
import re
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

from app.bot import DAILY_REMINDER_START, DATABASE_URL, TOKEN, init_db

# Mocking the Update object for Telegram

load_dotenv()


def test_api_token():
    token = os.getenv("TELEGRAM_TOKEN")
    assert token is not None
    assert TOKEN == token


def test_database_url():
    url = os.getenv("DATABASE_URL")
    assert url is not None
    assert DATABASE_URL == url


def test_daily_reminder_start():
    pattern = re.compile(r'^([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$')
    assert pattern.match(DAILY_REMINDER_START) is not None


def test_init_db():
    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        init_db()  # Assuming the import from the bot script
        expected_sql = """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            description TEXT,
            category TEXT,
            deadline TEXT,
            completed BOOLEAN DEFAULT 0
        )
    """.strip()
        mock_cursor.execute.assert_called_with(expected_sql)
        assert mock_connect.return_value.commit.called
        assert mock_connect.return_value.close.called
