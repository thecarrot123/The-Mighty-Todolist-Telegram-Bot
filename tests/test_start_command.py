from unittest.mock import AsyncMock, MagicMock

import pytest
from dotenv import load_dotenv

from app.bot import start_command

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
async def test_start_command():
    """
    Tests the start_command function to ensure it sends the correct welcome
    message when the bot is first interacted with by a user. Verifies the
    appropriate response is triggered upon the '/start' command.
    """
    update = MockUpdate("/start", user_id=12345)
    context = MagicMock()

    await start_command(update, context)

    update.message.reply_text.assert_called_with(
        "Welcome to The Mighty To-Do List Bot!"
    )
