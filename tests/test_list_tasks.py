import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv

from app.bot import list_tasks

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
async def test_list_tasks_with_no_tasks():
    user_id = 12345
    update = MockUpdate("/list", user_id)
    context = MagicMock()

    with patch('sqlite3.connect') as mock_connect:
        mock_connection = mock_connect.return_value
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchall.return_value = []  # No tasks in the database

        await list_tasks(update, context)

        # Assert it sends the correct message when no tasks are found
        update.message.reply_text.assert_awaited_once_with("No tasks found.")


@pytest.mark.asyncio
async def test_list_tasks_with_db_error():
    update = MockUpdate("/list", user_id=12345)
    context = MagicMock()

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

        await list_tasks(update, context)

        mocked_logging.assert_called_with(
            "Database error: Forced database error"
        )
        update.message.reply_text.assert_called_once_with(
            "Failed to list task due to a database error."
        )


@pytest.mark.asyncio
async def test_list_tasks_unexpected_error():
    update = MockUpdate("/list", user_id=12345)
    context = MagicMock()

    with patch('logging.error') as mocked_logging, patch(
        'sqlite3.connect'
    ) as mocked_connect:

        mocked_connect.side_effect = Exception("Forced error")

        await list_tasks(update, context)

        mocked_logging.assert_called_with("Unexpected error: Forced error")
        update.message.reply_text.assert_called_once_with(
            "Failed to list task due to an unexpected error."
        )


@pytest.mark.asyncio
async def test_list_tasks_with_multiple_tasks():
    user_id = 12345
    update = MockUpdate("/list", user_id)
    context = MagicMock()

    with patch('sqlite3.connect') as mock_connect:
        mock_connection = mock_connect.return_value
        mock_cursor = mock_connection.cursor.return_value
        # Simulate returned tasks
        mock_cursor.fetchall.return_value = [
            (1, 'Task 1', 'Work', 0, '2023-01-01 12:00'),
            (2, 'Task 2', 'Home', 0, '2023-01-02 12:00'),
        ]

        await list_tasks(update, context)

        expected_message = (
            "id: description - category - completed - due by deadline\n"
            "1: Task 1 - Work - False - due by 2023-01-01 12:00\n"
            "2: Task 2 - Home - False - due by 2023-01-02 12:00"
        )
        update.message.reply_text.assert_awaited_once_with(expected_message)
