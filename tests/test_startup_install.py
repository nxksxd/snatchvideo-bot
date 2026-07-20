"""Regression tests for interactive installation and admin startup notification."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("ADMIN_ID", "448795617")

from bot import notify_admin_started


class FakeBot:
    def __init__(self):
        self.calls = []

    async def send_message(self, **kwargs):
        self.calls.append(kwargs)


class StartupNotificationTests(unittest.IsolatedAsyncioTestCase):
    async def test_notification_is_sent_only_to_configured_admin(self):
        bot = FakeBot()

        with patch("bot.config.ADMIN_ID", 448795617):
            await notify_admin_started(bot)

        self.assertEqual(
            bot.calls,
            [{"chat_id": 448795617, "text": "✅ SnatchVideo Bot успешно установлен и запущен."}],
        )


class InstallerPromptTests(unittest.TestCase):
    def test_invalid_admin_id_prints_error_instead_of_appearing_frozen(self):
        installer = Path(__file__).parents[1].joinpath("install.sh").read_text()

        self.assertIn("Telegram ID должен содержать только цифры", installer)


if __name__ == "__main__":
    unittest.main()
