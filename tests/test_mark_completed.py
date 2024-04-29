import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv

from app.bot import mark_completed

# Mocking the Update object for Telegram

load_dotenv()


class MockUpdate:
    def __init__(self, message_text, user_id, chat_id=1):
        self.message = MagicMock()
        self.message.text = message_text
        self.effective_user = MagicMock()
        self.effective_user.id = user_id
        self.effective_chat = MagicMock()
        self.effective_chat.id = chat_id
        self.message.reply_text = AsyncMock()


@pytest.mark.asyncio
async def test_mark_completed_success():
    update = MockUpdate("/complete", user_id=12345)
    context = MagicMock()
    context.args = ["42"]

    with patch('sqlite3.connect') as mock_connect:
        mock_connection = mock_connect.return_value
        mock_cursor = mock_connection.cursor.return_value
        # Task exists and is not completed
        mock_cursor.fetchone.return_value = [42]

        await mark_completed(update, context)

        update.message.reply_text.assert_awaited_once_with(
            "Task marked as completed successfully!"
        )
        mock_cursor.execute.assert_any_call(
            "UPDATE tasks SET completed = TRUE WHERE id = ? AND user_id = ?",
            (42, 12345),
        )


@pytest.mark.asyncio
async def test_mark_completed_tasks_with_db_error():
    update = MockUpdate("/complete", user_id=12345)
    context = MagicMock()
    context.args = ["42"]

    with patch('logging.error') as mocked_logging, patch(
        'sqlite3.connect'
    ) as mocked_connect:
        mocked_conn = MagicMock()
        mocked_cursor = MagicMock()
        mocked_connect.return_value = mocked_conn
        mocked_conn.cursor.return_value = mocked_cursor
        mocked_cursor.execute.side_effect = sqlite3.Error(
            "Forced database error"
        )

        await mark_completed(update, context)

        mocked_logging.assert_called_with(
            "Database error: Forced database error"
        )
        update.message.reply_text.assert_called_once_with(
            "Failed to complete task due to a database error."
        )


@pytest.mark.asyncio
async def test_mark_completed_tasks_unexpected_error():
    update = MockUpdate("/complete", user_id=12345)
    context = MagicMock()
    context.args = ["42"]

    with patch('logging.error') as mocked_logging, patch(
        'sqlite3.connect'
    ) as mocked_connect:

        mocked_connect.side_effect = Exception("Forced error")

        await mark_completed(update, context)

        mocked_logging.assert_called_with("Unexpected error: Forced error")
        update.message.reply_text.assert_called_once_with(
            "Failed to complete task due to an unexpected error."
        )


@pytest.mark.asyncio
async def test_mark_completed_not_found():
    update = MockUpdate("/complete", user_id=12345)
    context = MagicMock()
    context.args = ["100"]

    with patch('sqlite3.connect') as mock_connect:
        mock_connection = mock_connect.return_value
        mock_cursor = mock_connection.cursor.return_value
        # Task does not exist or already completed
        mock_cursor.fetchone.return_value = None

        await mark_completed(update, context)

        update.message.reply_text.assert_awaited_once_with(
            "Task not found or already completed."
        )


@pytest.mark.asyncio
async def test_mark_completed_db_error():
    update = MockUpdate("/complete", user_id=12345)
    context = MagicMock()
    context.args = ["42"]

    with patch('sqlite3.connect') as mock_connect:
        mock_connect.side_effect = sqlite3.Error("DB connection failed")

        await mark_completed(update, context)

        update.message.reply_text.assert_awaited_once_with(
            "Failed to complete task due to a database error."
        )
