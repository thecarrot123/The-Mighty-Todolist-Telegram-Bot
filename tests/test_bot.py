import pytest
from unittest.mock import Mock, AsyncMock
from bot import start_command

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
    update.message.reply_text.assert_called_with("Welcome to The Mighty To-Do List Bot!")
