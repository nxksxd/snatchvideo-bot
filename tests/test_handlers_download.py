import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

from handlers import download as download_module
from handlers.states import DownloadStates


class HandleLinkInvalidTextTests(unittest.TestCase):
    """Verify handle_link replies appropriately for non-URL text per FSM state."""

    def _run(self, current_state, text="not a url"):
        message = MagicMock()
        message.chat.type = "private"
        message.text = text
        message.answer = AsyncMock()

        state = MagicMock()
        state.get_state = AsyncMock(return_value=current_state)
        state.get_data = AsyncMock(return_value={"bot_messages": []})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()

        bot = MagicMock()

        asyncio.run(download_module.handle_link(message, state, bot))
        return message

    def test_waiting_quality_state_gets_quality_hint(self):
        message = self._run(DownloadStates.waiting_quality.state)
        message.answer.assert_called_once()
        args, _ = message.answer.call_args
        self.assertIn("ожидается выбор качества", args[0])

    def test_waiting_link_state_gets_link_error(self):
        message = self._run(DownloadStates.waiting_link.state)
        message.answer.assert_called_once()
        args, _ = message.answer.call_args
        self.assertIn("корректную ссылку", args[0])

    def test_no_state_silently_ignores_invalid_text(self):
        message = self._run(None)
        message.answer.assert_not_called()


class HandleLinkNoDeleteTests(unittest.TestCase):
    """Verify handle_link does NOT call message.delete() (was always failing in private chats)."""

    def test_message_delete_not_called(self):
        message = MagicMock()
        message.chat.type = "private"
        message.chat.id = 1
        message.from_user.id = 42
        message.from_user.username = "u"
        message.from_user.first_name = "F"
        message.from_user.last_name = "L"
        message.text = "https://example.com/path"
        message.answer = AsyncMock()
        message.delete = AsyncMock()

        state = MagicMock()
        state.get_state = AsyncMock(return_value=DownloadStates.waiting_link.state)
        state.get_data = AsyncMock(return_value={"bot_messages": []})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()

        bot = MagicMock()

        asyncio.run(download_module.handle_link(message, state, bot))

        message.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
