import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv

from app.bot import list_tasks

# Mocking the Update object for Telegram

load_dotenv()


class MockUpdate:
    """
    Mocks Telegram's Update object for testing. Simulates the structure and
    behavior of the Telegram Bot API's Update object, including user and chat
    identification and reply methods.
    """
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
    """
    Tests the list_tasks function to ensure it correctly handles the scenario
    where no tasks are present in the database. This test verifies that
    the appropriate message "No tasks found." is sent to the user.
    """
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
    """
    Simulates a database error during the retrieval of tasks to test the bot's
    error handling capabilities. This test ensures that the function logs the
    error and informs user of a failure to list tasks due to a database error.
    """
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
    """
    Simulates an unexpected error to test how the list_tasks function handles
    unexpected situations and communicates failure to the user. This test
    verifies the bot's ability to log unexpected errors and provide a user
    message that indicates a failure to list tasks.
    """
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
    """
    Tests the list_tasks function to ensure it correctly formats and sends a
    message listing multiple tasks. This test checks the function's ability to
    construct a detailed message including task details such as description,
    category, completion status, and deadline, and then sends it correctly.
    """
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
