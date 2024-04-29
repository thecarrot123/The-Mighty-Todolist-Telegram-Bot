import sqlite3
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from dotenv import load_dotenv

from app.bot import (notify_due_tasks, run_notifiers)

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
async def test_notify_due_tasks():
    """
    Tests the notification of due tasks, ensuring the bot sends a reminder for
    tasks due within 24 hours.
    Verifies correct message formatting and delivery.
    """
    bot = MagicMock()
    bot.send_message = AsyncMock()
    with patch("sqlite3.connect") as mock_connect, \
            patch("app.bot.Bot.send_message"):
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [(1, 12345, "Prepare meeting")]
        await notify_due_tasks(bot)
        bot.send_message.assert_called_with(
            chat_id=12345,
            text="Reminder: Task 'Prepare meeting' is due in 24 hours!",
        )


@pytest.mark.asyncio
@patch('sqlite3.connect')
async def test_notify_due_tasks_success(mock_connect):
    """
    Tests multiple notifications for due tasks, ensuring each task reminder is
    sent correctly and verifies the call count matches expected tasks.
    """
    bot = MagicMock()
    bot.send_message = AsyncMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        (1, 12345, 'Task 1'),  # Assume user_id should be an integer
        (2, 67890, 'Task 2'),  # Same here, use integer for user_id
    ]

    await notify_due_tasks(bot)

    assert bot.send_message.call_count == 2
    bot.send_message.assert_has_calls(
        [
            call(
                chat_id=12345,
                text="Reminder: Task 'Task 1' is due in 24 hours!",
            ),
            call(
                chat_id=67890,
                text="Reminder: Task 'Task 2' is due in 24 hours!",
            ),
        ],
        any_order=True,
    )


@pytest.mark.asyncio
async def test_notify_due_tasks_db_error():
    """
    Simulates a database error during the task notification process to test
    the bot's error handling and logging capabilities.
    """
    bot = MagicMock()
    bot.send_message = AsyncMock()

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

        await notify_due_tasks(bot)

        mocked_logging.assert_called_with(
            "Database error during notification: Forced database error"
        )


@pytest.mark.asyncio
async def test_notify_due_tasks_unexpected_error():
    """
    Tests the bot's response to unexpected errors during task notifications,
    ensuring proper logging and error handling.
    """
    bot = MagicMock()
    bot.send_message = AsyncMock()

    with patch('logging.error') as mocked_logging, patch(
        'sqlite3.connect'
    ) as mocked_connect:

        mocked_connect.side_effect = Exception("Forced error")

        await notify_due_tasks(bot)

        mocked_logging.assert_called_with(
            "Unexpected error during notification: Forced error"
        )


def test_notification_triggered():
    """
    Tests the triggering of notifications based on the daily reminder time.
    Ensures the notifier is triggered at the correct time and verifies that
    the notification function is called as expected.
    """
    now = datetime.now().strftime("%H:%M:%S")

    with patch('app.bot.DAILY_REMINDER_START', now), \
        patch('app.bot.Bot'), \
        patch('app.bot.asyncio.run', new_callable=MagicMock) as mock_run, \
        patch('app.bot.shutdown_event.wait'), \
        patch('app.bot.notify_due_tasks', new_callable=MagicMock), \
        patch('app.bot.shutdown_event.is_set',
              side_effect=[False, False, True]):

        run_notifiers()

        mock_run.assert_called_once()
