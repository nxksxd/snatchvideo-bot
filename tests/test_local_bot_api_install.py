"""Installer contract for the local Telegram Bot API service."""

import unittest
from pathlib import Path


INSTALLER = Path(__file__).parents[1] / "install.sh"


class LocalBotApiInstallerTests(unittest.TestCase):
    def setUp(self):
        self.script = INSTALLER.read_text()

    def test_installer_reuses_existing_docker_instead_of_forcing_ubuntu_package(self):
        self.assertIn("if ! command -v docker", self.script)
        self.assertNotIn("curl docker.io ffmpeg", self.script)

    def test_installer_skips_apt_when_required_commands_are_already_installed(self):
        self.assertIn("MISSING_PACKAGES=()", self.script)
        self.assertIn('if (( ${#MISSING_PACKAGES[@]} )); then', self.script)
        self.assertNotIn("apt-get install -y ca-certificates curl ffmpeg git python3 python3-venv", self.script)

    def test_deno_install_is_non_interactive(self):
        self.assertIn("DENO_NO_UPDATE_CHECK=1", self.script)
        self.assertIn("-y", self.script)

    def test_dependency_install_has_timeout_and_visible_completion_marker(self):
        self.assertIn("timeout 180", self.script)
        self.assertIn("Зависимости Python установлены", self.script)

    def test_installer_prompts_for_api_credentials_without_echoing_hash(self):
        self.assertIn("TELEGRAM_API_ID", self.script)
        self.assertIn("Ожидается ввод в терминале", self.script)
        self.assertIn('read -r TELEGRAM_API_ID', self.script)
        self.assertIn('read -r -s TELEGRAM_API_HASH', self.script)

    def test_installer_creates_loopback_only_local_api_service(self):
        self.assertIn("telegram-bot-api.service", self.script)
        self.assertIn("--http-port=8081", self.script)
        self.assertIn("--local", self.script)
        self.assertIn("127.0.0.1:8081:8081", self.script)

    def test_installer_enables_local_api_in_bot_environment(self):
        self.assertIn("'USE_LOCAL_BOT_API': 'true'", self.script)
        self.assertIn("'TELEGRAM_API_BASE': 'http://127.0.0.1:8081'", self.script)
        self.assertIn("'MAX_FILE_SIZE_MB': '2000'", self.script)


if __name__ == "__main__":
    unittest.main()
