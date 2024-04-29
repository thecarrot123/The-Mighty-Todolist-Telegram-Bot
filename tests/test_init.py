import os
import re
from unittest.mock import MagicMock, patch

from dotenv import load_dotenv

from app.bot import DAILY_REMINDER_START, DATABASE_URL, TOKEN, init_db

# Mocking the Update object for Telegram

load_dotenv()


def test_api_token():
    """
    Tests that the TELEGRAM_TOKEN is correctly set in the environment and
    matches the expected token stored in the TOKEN constant.
    This ensures that the environment is correctly configured
    for the bot to authenticate with Telegram.
    """
    token = os.getenv("TELEGRAM_TOKEN")
    assert token is not None
    assert TOKEN == token


def test_database_url():
    """
    Tests that the DATABASE_URL is properly set in the environment and verifie
    it matches the DATABASE_URL constant. This is crucial for ensuring the bot
    can successfully connect to the expected database.
    """
    url = os.getenv("DATABASE_URL")
    assert url is not None
    assert DATABASE_URL == url


def test_daily_reminder_start():
    """
    Validates that the DAILY_REMINDER_START time is a correct HH:MM:SS format.
    This test confirms the time pattern validity to prevent scheduling errors.
    """
    pattern = re.compile(r'^([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$')
    assert pattern.match(DAILY_REMINDER_START) is not None


def test_init_db():
    """
    Tests the initialization of the database, ensuring that the SQL command to
    create the tasks table is executed correctly. This function checks if the
    table creation process is handled as expected, including if the database
    commits and closes the connection properly.
    """
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
