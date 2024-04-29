from unittest.mock import AsyncMock, MagicMock

import pytest
from dotenv import load_dotenv

from app.bot import help_command

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
async def test_help_command():
    """
    Tests the help_command function to ensure it responds with the correct help
    message. This test verifies that the function sends a comprehensive guide
    outlining all the bot commands and their usage.
    """
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
