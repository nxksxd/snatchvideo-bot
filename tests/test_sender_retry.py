"""Tests for MediaSender._send_with_retry — robustness against Telegram API errors."""

import asyncio
import os
import unittest

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

from aiogram.exceptions import (
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)

from services.sender import MediaSender


class _FakeMethod:
    """Stand-in for an aiogram TelegramMethod required by exception ctors."""


class SendWithRetryTests(unittest.TestCase):
    def setUp(self):
        self.sender = MediaSender()

    def _run(self, factory, retries=2, delay=0):
        return asyncio.run(self.sender._send_with_retry(factory, retries=retries, delay=delay))

    def test_returns_immediately_on_success(self):
        async def factory():
            return "ok"

        result = self._run(factory)
        self.assertEqual(result, "ok")

    def test_retries_on_telegram_retry_after_then_succeeds(self):
        calls = {"n": 0}

        async def factory():
            calls["n"] += 1
            if calls["n"] == 1:
                raise TelegramRetryAfter(method=_FakeMethod(), message="429", retry_after=0)
            return "ok"

        result = self._run(factory)
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 2)

    def test_retries_on_telegram_server_error_then_succeeds(self):
        calls = {"n": 0}

        async def factory():
            calls["n"] += 1
            if calls["n"] < 2:
                raise TelegramServerError(method=_FakeMethod(), message="500 internal")
            return "ok"

        result = self._run(factory)
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 2)

    def test_retries_on_telegram_network_error_then_succeeds(self):
        calls = {"n": 0}

        async def factory():
            calls["n"] += 1
            if calls["n"] < 2:
                raise TelegramNetworkError(method=_FakeMethod(), message="connection reset")
            return "ok"

        result = self._run(factory)
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 2)

    def test_gives_up_after_retries_and_reraises(self):
        async def factory():
            raise TelegramServerError(method=_FakeMethod(), message="500 internal")

        with self.assertRaises(TelegramServerError):
            self._run(factory, retries=1)

    def test_non_retriable_exception_is_reraised_immediately(self):
        calls = {"n": 0}

        class CustomError(Exception):
            pass

        async def factory():
            calls["n"] += 1
            raise CustomError("bad request")

        with self.assertRaises(CustomError):
            self._run(factory, retries=2)
        # No retries — non-timeout, non-Telegram-typed errors propagate immediately.
        self.assertEqual(calls["n"], 1)

    def test_legacy_timeout_substring_path_still_retries(self):
        """Backward-compat: legacy 'timeout' substring matching still works."""
        calls = {"n": 0}

        async def factory():
            calls["n"] += 1
            if calls["n"] < 2:
                raise RuntimeError("read timeout while uploading")
            return "ok"

        result = self._run(factory)
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 2)


if __name__ == "__main__":
    unittest.main()
