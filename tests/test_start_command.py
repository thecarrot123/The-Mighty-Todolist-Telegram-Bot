from unittest.mock import AsyncMock, MagicMock

import pytest
from dotenv import load_dotenv

from app.bot import start_command

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
