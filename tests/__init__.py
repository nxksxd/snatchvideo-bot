"""
Test package init.

Sets a placeholder ``TELEGRAM_BOT_TOKEN`` once before any test module is imported,
so individual test files don't need to repeat ``os.environ.setdefault(...)``.
``Settings.from_env()`` requires the token to be present even when its value
isn't actually used by the test (e.g. tests that exercise utils.is_supported_url
hit ``config.SUPPORTED_VIDEO_DOMAINS`` which lazily resolves to ``settings``).

If you're writing a NEW test that doesn't need any settings/config attribute,
you can still avoid env-coupling by using ``Settings.for_tests(**overrides)``
and passing the result directly to whatever you're testing.
"""

import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
