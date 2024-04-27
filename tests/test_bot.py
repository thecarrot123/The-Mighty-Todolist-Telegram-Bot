import pytest
from unittest.mock import Mock, AsyncMock, call
from app.bot import (
    start_command,
    help_command,
    init_db,
    add_task,
    notify_due_tasks,
    list_tasks,
    delete_task,
    mark_completed,
)
import sqlite3
from unittest.mock import patch

# Mocking the Update object for Telegram


class MockUpdate:
    def __init__(self, message_text, user_id):
        self.message = Mock()
        self.message.text = message_text
        self.effective_user = Mock()
        self.effective_user.id = user_id
        self.message.reply_text = AsyncMock()


# Example usage in a test


@pytest.mark.asyncio
async def test_start_command():
    # Create a mock Update object with specific attributes
    update = MockUpdate("/start", user_id=12345)
    context = Mock()  # Similarly mock the CallbackContext if needed

    # Correct usage without asyncio.run
    await start_command(update, context)

    # Assert that reply_text was called with the expected welcome message
    update.message.reply_text.assert_called_with(
        "Welcome to The Mighty To-Do List Bot!"
    )


@pytest.mark.asyncio
async def test_help_command():
    update = MockUpdate("/help", user_id=12345)
    context = Mock()
    await help_command(update, context)

    expected_help_text = (
        "Here are the commands you can use with this bot:\n"
        "/start - Start interacting with the bot.\n"
        "/add - Add a new task. Usage: /add <description>; <category>; <deadline>\n"
        "/list - List all your current tasks that are not yet completed.\n"
        "/delete - Delete a task. Usage: /delete <task_id>\n"
        "/complete - Mark a task as completed. Usage: /complete <task_id>\n"
        "/help - Show this help message."
    )
    update.message.reply_text.assert_called_with(expected_help_text)


def test_init_db():
    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = Mock()
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
    update = MockUpdate("/add", user_id=12345)
    context = Mock()
    context.args = ["Prepare presentation; work; 2023-10-15 22:20"]
    with patch("sqlite3.connect") as mock_connect:
        mock_cursor = Mock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        await add_task(update, context)
        mock_cursor.execute.assert_called()
        update.message.reply_text.assert_called_with(
            "Task added successfully!"
        )


@pytest.mark.asyncio
async def test_notify_due_tasks():
    with patch("sqlite3.connect") as mock_connect, patch(
        "app.bot.Bot.send_message"
    ) as mock_send_message:
        mock_cursor = Mock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [(1, 12345, "Prepare meeting")]
        await notify_due_tasks()
        mock_send_message.assert_called_with(
            chat_id=12345,
            text="Reminder: Task 'Prepare meeting' is due in 24 hours!",
        )


@pytest.mark.asyncio
async def test_list_tasks_with_no_tasks():
    user_id = 12345
    update = MockUpdate("/list", user_id)
    context = Mock()

    with patch('sqlite3.connect') as mock_connect:
        mock_connection = mock_connect.return_value
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchall.return_value = []  # No tasks in the database

        await list_tasks(update, context)

        # Assert it sends the correct message when no tasks are found
        update.message.reply_text.assert_awaited_once_with("No tasks found.")


@pytest.mark.asyncio
async def test_list_tasks_with_multiple_tasks():
    user_id = 12345
    update = MockUpdate("/list", user_id)
    context = Mock()

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
async def test_list_tasks_db_error():
    user_id = 12345
    update = MockUpdate("/list", user_id)
    context = Mock()

    with patch('sqlite3.connect') as mock_connect:
        mock_connect.side_effect = sqlite3.Error("DB connection failed")

        await list_tasks(update, context)

        # Assert it sends the error message
        update.message.reply_text.assert_awaited_once_with(
            "Failed to add task due to a database error."
        )


@pytest.mark.asyncio
async def test_mark_completed_success():
    update = MockUpdate("/complete", user_id=12345)
    context = Mock()
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
async def test_mark_completed_not_found():
    update = MockUpdate("/complete", user_id=12345)
    context = Mock()
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
    context = Mock()
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
    context = Mock()
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
    context = Mock()
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
async def test_delete_task_db_error():
    update = MockUpdate("/delete", user_id=12345)
    context = Mock()
    context.args = ["3"]

    with patch('sqlite3.connect') as mock_connect:
        mock_connect.side_effect = sqlite3.Error("DB connection failed")

        await delete_task(update, context)

        update.message.reply_text.assert_awaited_once_with(
            "Failed to delete task due to a database error."
        )


@pytest.mark.asyncio
@patch('sqlite3.connect')
async def test_notify_due_tasks_success(mock_connect):
    bot = Mock()
    bot.send_message = AsyncMock()
    mock_cursor = Mock()
    mock_connect.return_value.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        (1, 12345, 'Task 1'),  # Assume user_id should be an integer
        (2, 67890, 'Task 2')   # Same here, use integer for user_id
    ]

    await notify_due_tasks(bot)

    assert bot.send_message.call_count == 2
    bot.send_message.assert_has_calls([
        call(chat_id=12345, text="Reminder: Task 'Task 1' is due in 24 hours!"),
        call(chat_id=67890, text="Reminder: Task 'Task 2' is due in 24 hours!")
    ], any_order=True)

@pytest.mark.asyncio
@patch('sqlite3.connect')
async def test_notify_due_tasks_db_error(mock_connect):
    mock_connect.side_effect = sqlite3.Error("Database connection failed")
    bot = Mock()
    bot.send_message = AsyncMock()
    with patch('logging.error') as mock_log_error:
        await notify_due_tasks(bot)
        mock_log_error.assert_called_with("Database error during notification: Database connection failed")

    assert bot.send_message.call_count == 0