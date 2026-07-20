"""Tests for handler-level chat-type filters."""

import os
import unittest

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

from handlers.common import router as common_router
from handlers.download import router as download_router
from handlers.stats import router as stats_router


class RouterChatTypeFilterTests(unittest.TestCase):
    """Each user-facing router filters out non-private chats at the router level.

    The check is structural: ``router.message._handler.filters`` is the list of
    filter callbacks added via ``router.message.filter(...)``. We don't assert
    a specific filter object, just that at least one router-level filter exists
    on the message observer — that's what was missing before this PR.
    """

    def test_common_router_has_message_filter(self):
        self.assertGreater(
            len(common_router.message._handler.filters), 0,
            "common router has no router-level message filter"
        )

    def test_download_router_has_message_filter(self):
        self.assertGreater(
            len(download_router.message._handler.filters), 0,
            "download router has no router-level message filter"
        )

    def test_download_router_has_callback_filter(self):
        self.assertGreater(
            len(download_router.callback_query._handler.filters), 0,
            "download router has no router-level callback_query filter"
        )

    def test_stats_router_has_message_filter(self):
        self.assertGreater(
            len(stats_router.message._handler.filters), 0,
            "stats router has no router-level message filter"
        )


if __name__ == "__main__":
    unittest.main()
