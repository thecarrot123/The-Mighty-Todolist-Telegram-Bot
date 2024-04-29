import os
import re
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import pytest
from dotenv import load_dotenv

from app.bot import (DAILY_REMINDER_START, DATABASE_URL, TOKEN, add_task,
                     delete_task, help_command, init_db, list_tasks, main,
                     mark_completed, notify_due_tasks, run_notifiers,
                     start_command)

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


@pytest.mark.asyncio
async def test_start_command():
    # Create a mock Update object with specific attributes
    update = MockUpdate("/start", user_id=12345)
    context = MagicMock()  # Similarly mock the CallbackContext if needed

    # Correct usage without asyncio.run
    await start_command(update, context)

    # Assert that reply_text was called with the expected welcome message
    update.message.reply_text.assert_called_with(
        "Welcome to The Mighty To-Do List Bot!"
    )


@pytest.mark.asyncio
async def test_help_command():
    update = MockUpdate("/help", user_id=12345)
    context = MagicMock()
    await help_command(update, context)

    expected_help_text = (
        "Here are the commands you can use with this bot:\n"
        "/start - Start interacting with the bot.\n"
        """/add - Add a new task. """
        """Usage: /add <description>; <category>; <deadline>\n"""
        "/list - List all your current tasks that are not yet completed.\n"
        "/delete - Delete a task. Usage: /delete <task_id>\n"
        "/complete - Mark a task as completed. Usage: /complete <task_id>\n"
        "/help - Show this help message."
    )
    update.message.reply_text.assert_called_with(expected_help_text)


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


@pytest.mark.asyncio
async def test_add_task_valid_input():
    future = datetime.now() + timedelta(minutes=10)
    future = future.strftime("%Y-%m-%d %H:%M")

    update = MockUpdate("/add", user_id=12345)
    context = MagicMock()
    context.args = [f"Prepare presentation; work; {future}"]

    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor

        await add_task(update, context)

        mock_cursor.execute.assert_called()
        update.message.reply_text.assert_called_with(
            "Task added successfully!"
        )


@pytest.mark.asyncio
async def test_add_task_invalid_input1():
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


@pytest.mark.asyncio
async def test_notify_due_tasks():
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


@pytest.mark.asyncio
async def test_delete_task_success():
    update = MockUpdate("/delete", user_id=12345)
    context = MagicMock()
    context.args = ["3"]

    with patch('sqlite3.connect') as mock_connect:
        mock_connection = mock_connect.return_value
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchone.return_value = [3]  # Task exists

        await delete_task(update, context)

        mock_cursor.execute.assert_any_call(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?", (3, 12345)
        )
        update.message.reply_text.assert_awaited_once_with(
            "Task deleted successfully!"
        )


@pytest.mark.asyncio
async def test_delete_task_not_found():
    update = MockUpdate("/delete", user_id=12345)
    context = MagicMock()
    context.args = ["99"]

    with patch('sqlite3.connect') as mock_connect:
        mock_connection = mock_connect.return_value
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchone.return_value = None  # Task does not exist

        await delete_task(update, context)

        update.message.reply_text.assert_awaited_once_with(
            "Task not found or does not belong to you."
        )


@pytest.mark.asyncio
async def test_delete_tasks_with_db_error():
    update = MockUpdate("/delete", user_id=12345)
    context = MagicMock()
    context.args = ["4"]

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

        await delete_task(update, context)

        mocked_logging.assert_called_with(
            "Database error: Forced database error"
        )
        update.message.reply_text.assert_called_once_with(
            "Failed to delete task due to a database error."
        )


@pytest.mark.asyncio
async def test_delete_tasks_unexpected_error():
    update = MockUpdate("/delete", user_id=12345)
    context = MagicMock()
    context.args = ["4"]

    with patch('logging.error') as mocked_logging, patch(
        'sqlite3.connect'
    ) as mocked_connect:

        mocked_connect.side_effect = Exception("Forced error")

        await delete_task(update, context)

        mocked_logging.assert_called_with("Unexpected error: Forced error")
        update.message.reply_text.assert_called_once_with(
            "Failed to delete task due to an unexpected error."
        )


@pytest.mark.asyncio
@patch('sqlite3.connect')
async def test_notify_due_tasks_success(mock_connect):
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
    now = datetime.now().strftime("%H:%M:%S")

    with patch('app.bot.DAILY_REMINDER_START', now), \
        patch('app.bot.Bot'), \
        patch('app.bot.asyncio.run', new_callable=MagicMock) as mock_async_run, \
        patch('app.bot.shutdown_event.wait'), \
        patch('app.bot.notify_due_tasks', new_callable=MagicMock), \
        patch('app.bot.shutdown_event.is_set',
              side_effect=[False, False, True]):

        run_notifiers()

        mock_async_run.assert_called_once()


def test_main_db_init():
    with patch('app.bot.init_db') as mock_init_db, patch(
        'app.bot.Application.builder'
    ), patch('app.bot.run_notifiers'):

        main()

        # Check if database is initialized
        mock_init_db.assert_called_once()


def test_main_command_handler():
    with patch('app.bot.init_db'), patch(
        'app.bot.Application.builder'
    ) as mock_builder, patch(
        'app.bot.CommandHandler'
    ) as mock_command_handler, patch(
        'app.bot.run_notifiers'
    ):

        mock_application = MagicMock()
        mock_builder.return_value.token.return_value.build.return_value = (
            mock_application
        )

        main()

        # Check that all handlers are added
        expected_handlers = [
            ("start", start_command),
            ("help", help_command),
            ("add", add_task),
            ("list", list_tasks),
            ("delete", delete_task),
            ("complete", mark_completed),
        ]

        # Check that all handlers are added with correct callbacks
        actual_calls = [c[0] for c in mock_command_handler.call_args_list]
        assert (actual_calls == expected_handlers)


def test_main_threading():
    with patch('app.bot.init_db'), patch('app.bot.Application.builder'), patch(
        'app.bot.run_notifiers'
    ), patch('app.bot.Thread') as mock_thread:

        main()

        # Ensure the thread for running notifiers is started
        mock_thread.assert_called_once_with(target=ANY)
        assert (
            mock_thread.return_value.start.called
        ), "Notifier thread should start"
