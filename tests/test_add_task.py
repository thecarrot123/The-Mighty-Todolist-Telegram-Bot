import sqlite3
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv

from app.bot import add_task

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
async def test_add_task_valid_input():
    """
    Ensures the add_task function handles valid input correctly by adding the
    task and sending a success message.
    """
    future = datetime.now() + timedelta(minutes=10)
    future = future.strftime("%Y-%m-%d %H:%M")

    update = MockUpdate("/add", user_id=12345)
    context = MagicMock()
    context.args = [f"Prepare presentation; work; {future}"]

    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        task_id = mock_cursor.lastrowid

        await add_task(update, context)

        mock_cursor.execute.assert_called()
        update.message.reply_text.assert_called_with(
            f"Task {task_id} added successfully!"
        )


@pytest.mark.asyncio
async def test_add_task_invalid_input1():
    """
    Verifies add_task response to empty input, ensuring no database operation
    is attempted and correct usage is communicated.
    """
    update = MockUpdate("/add", user_id=12345)
    context = MagicMock()
    context.args = [""]

    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor

        await add_task(update, context)

        mock_cursor.execute.assert_not_called()
        update.message.reply_text.assert_called_with(
            """Usage:
                /add <description>; <category>; <deadline: YYYY-MM-DD HH:MM>
                """
        )


@pytest.mark.asyncio
async def test_add_task_invalid_input2():
    """
    Checks add_task's handling of input with only a description, ensuring it
    prompts with correct usage instructions.
    """
    update = MockUpdate("/add", user_id=12345)
    context = MagicMock()
    context.args = ["Prepare presentation"]
    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor

        await add_task(update, context)

        mock_cursor.execute.assert_not_called()
        update.message.reply_text.assert_called_with(
            """Usage:
                /add <description>; <category>; <deadline: YYYY-MM-DD HH:MM>
                """
        )


@pytest.mark.asyncio
async def test_add_task_invalid_input3():
    """
    Tests add_task's response to input missing the deadline, ensuring correct
    format usage message is returned.
    """
    update = MockUpdate("/add", user_id=12345)
    context = MagicMock()
    context.args = ["Prepare presentation; work"]

    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor

        await add_task(update, context)

        mock_cursor.execute.assert_not_called()
        update.message.reply_text.assert_called_with(
            """Usage:
                /add <description>; <category>; <deadline: YYYY-MM-DD HH:MM>
                """
        )


@pytest.mark.asyncio
async def test_add_task_invalid_input4():
    """
    Ensures add_task validates time format correctly, responding with an error
    message for incorrect time components.
    """
    update = MockUpdate("/add", user_id=12345)
    context = MagicMock()
    context.args = ["Prepare presentation; work; 25:50:21"]

    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor

        await add_task(update, context)

        mock_cursor.execute.assert_not_called()
        update.message.reply_text.assert_called_with(
            "Invalid date format. Use YYYY-MM-DD HH:MM."
        )


@pytest.mark.asyncio
async def test_add_task_invalid_input5():
    """
    Checks how add_task handles a date not in the future, ensuring it
    appropriately identifies and rejects such dates.
    """
    update = MockUpdate("/add", user_id=12345)
    context = MagicMock()
    context.args = ["Prepare presentation; work; 2023-10-15 22:20"]

    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor

        await add_task(update, context)

        mock_cursor.execute.assert_not_called()
        update.message.reply_text.assert_called_with(
            "The deadline must be in the future."
        )


@pytest.mark.asyncio
async def test_add_task_with_db_error():
    """
    Simulates a database error during the add_task operation to test error
    handling and logging functionality.
    """
    future = datetime.now() + timedelta(minutes=10)
    future = future.strftime("%Y-%m-%d %H:%M")

    update = MockUpdate("/add", user_id=12345)
    context = MagicMock()
    context.args = [f"Prepare presentation; work; {future}"]

    with patch('logging.error') as mocked_logging, patch(
        'sqlite3.connect'
    ) as mocked_connect:
        mocked_cursor = MagicMock()
        mocked_cursor.execute.side_effect = sqlite3.Error(
            "Forced database error"
        )
        mocked_conn = MagicMock()
        mocked_conn.cursor.return_value = mocked_cursor
        mocked_connect.return_value = mocked_conn

        await add_task(update, context)

        mocked_logging.assert_called_with(
            "Database error: Forced database error"
        )
        update.message.reply_text.assert_called_once_with(
            "Failed to add task due to a database error."
        )


@pytest.mark.asyncio
async def test_add_tasks_unexpected_error():
    """
    Simulates an unexpected error in add_task to verify the robustness of
    error handling and user communication.
    """
    future = datetime.now() + timedelta(minutes=10)
    future = future.strftime("%Y-%m-%d %H:%M")

    update = MockUpdate("/add", user_id=12345)
    context = MagicMock()
    context.args = [f"Prepare presentation; work; {future}"]
    context.job_queue = MagicMock()
    context.job_queue.run_once = MagicMock()

    with patch('logging.error') as mocked_logging, patch(
        'sqlite3.connect'
    ) as mocked_connect:

        mocked_connect.side_effect = Exception("Forced error")

        await add_task(update, context)

        mocked_logging.assert_called_with("Unexpected error: Forced error")
        update.message.reply_text.assert_called_once_with(
            "Failed to add task due to an unexpected error."
        )
