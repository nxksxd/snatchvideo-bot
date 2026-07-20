#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/snatchvideo-bot}"
REPO_URL="${REPO_URL:-https://github.com/nxksxd/snatchvideo-bot.git}"
SERVICE_NAME="snatchvideo-bot"

if [[ $EUID -ne 0 ]]; then
  exec sudo -E bash "$0" "$@"
fi

if ! command -v apt-get >/dev/null; then
  echo "Поддерживаются Ubuntu и Debian." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl ffmpeg git python3 python3-venv

if ! command -v deno >/dev/null; then
  DENO_INSTALL=/usr/local/lib/deno curl -fsSL https://deno.land/install.sh | sh
  ln -sf /usr/local/lib/deno/bin/deno /usr/local/bin/deno
fi

if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" fetch origin main
  git -C "$APP_DIR" checkout main
  git -C "$APP_DIR" reset --hard origin/main
else
  rm -rf "$APP_DIR"
  git clone --branch main --single-branch "$REPO_URL" "$APP_DIR"
fi

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [[ ! -f "$APP_DIR/.env" ]]; then
  if [[ ! -t 0 ]]; then
    exec </dev/tty
  fi

  BOT_TOKEN=""
  ADMIN_ID=""
  while [[ -z "$BOT_TOKEN" ]]; do
    read -r -s -p "Telegram Bot Token от @BotFather: " BOT_TOKEN || BOT_TOKEN=""
    echo
  done
  while true; do
    read -r -p "Ваш Telegram ID (ADMIN_ID, только цифры): " ADMIN_ID || ADMIN_ID=""
    ADMIN_ID="${ADMIN_ID//[[:space:]]/}"
    if [[ "$ADMIN_ID" =~ ^[0-9]+$ ]]; then
      break
    fi
    echo "Telegram ID должен содержать только цифры, без скобок и других символов. Повторите ввод." >&2
  done

  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  python3 - "$APP_DIR/.env" "$BOT_TOKEN" "$ADMIN_ID" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
text = text.replace("TELEGRAM_BOT_TOKEN=your_bot_token_here", f"TELEGRAM_BOT_TOKEN={sys.argv[2]}")
text = text.replace("ADMIN_ID=123456789", f"ADMIN_ID={sys.argv[3]}")
text = text.replace("STATS_DB_PATH=/path/to/stats.db", "STATS_DB_PATH=/var/lib/snatchvideo-bot/stats.db")
path.write_text(text)
PY
  chmod 600 "$APP_DIR/.env"
fi

install -d -m 750 /var/lib/snatchvideo-bot /var/lib/snatchvideo-bot/tmp
if ! grep -q '^STATS_DB_PATH=' "$APP_DIR/.env"; then
  printf '\nSTATS_DB_PATH=/var/lib/snatchvideo-bot/stats.db\nTEMP_DIR=/var/lib/snatchvideo-bot/tmp\n' >> "$APP_DIR/.env"
fi

cat > "/etc/systemd/system/$SERVICE_NAME.service" <<EOF
[Unit]
Description=SnatchVideo Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
Environment=PATH=$APP_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/bot.py
Restart=always
RestartSec=5
TimeoutStopSec=30
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=full
ReadWritePaths=/var/lib/snatchvideo-bot $APP_DIR

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 3
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  journalctl -u "$SERVICE_NAME" -n 100 --no-pager
  exit 1
fi

printf '\nSnatchVideo Bot установлен и запущен.\nСтатус: systemctl status %s\nЛоги: journalctl -u %s -f\nОбновление: повторите ту же команду установки.\n' "$SERVICE_NAME" "$SERVICE_NAME"
