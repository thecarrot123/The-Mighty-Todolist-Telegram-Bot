from unittest.mock import MagicMock, patch

from dotenv import load_dotenv

from app.bot import (add_task, delete_task, help_command, list_tasks, main,
                     mark_completed, start_command)

# Mocking the Update object for Telegram

load_dotenv()


def test_main_db_init():
    """
    Tests that the main function correctly initializes the database by calling
    the init_db function upon startup. Ensures that database initialization is
    a part of the app's startup routine.
    """
    with patch('app.bot.init_db') as mock_init_db, patch(
        'app.bot.Application.builder'
    ), patch('app.bot.run_notifiers'), \
            patch('app.bot.Thread'):

        main()

        # Check if database is initialized
        mock_init_db.assert_called_once()


def test_main_command_handler():
    """
    Tests that the main function correctly sets up all command handlers in the
    application. Verifies each command has the proper callback linked to the
    correct functionality.
    """
    with patch('app.bot.init_db'), patch(
        'app.bot.Application.builder'
    ) as mock_builder, patch(
        'app.bot.CommandHandler'
    ) as mock_command_handler, patch(
        'app.bot.run_notifiers'
    ), patch('app.bot.Thread'):

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
        assert actual_calls == expected_handlers


def test_main_threading():
    """
    Tests the main function's threading setup, specifically verifying that a
    thread for running notifiers is correctly initiated. Ensures the thread
    starts as expected, which is crucial for background tasks.
    """
    with patch('app.bot.init_db'), patch('app.bot.Application.builder'), patch(
        'app.bot.run_notifiers'
    ), patch('app.bot.Thread') as mock_thread:

        main()

        # Ensure the thread for running notifiers is started
        mock_thread.assert_called()
        assert (
            mock_thread.return_value.start.called
        ), "Notifier thread should start"
