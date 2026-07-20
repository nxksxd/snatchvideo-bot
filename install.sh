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
MISSING_PACKAGES=()
command -v curl >/dev/null || MISSING_PACKAGES+=(curl ca-certificates)
command -v ffmpeg >/dev/null || MISSING_PACKAGES+=(ffmpeg)
command -v git >/dev/null || MISSING_PACKAGES+=(git)
command -v python3 >/dev/null || MISSING_PACKAGES+=(python3)
python3 -c 'import venv' >/dev/null 2>&1 || MISSING_PACKAGES+=(python3-venv)
if (( ${#MISSING_PACKAGES[@]} )); then
  apt-get update
  apt-get install -y "${MISSING_PACKAGES[@]}"
fi

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sh /tmp/get-docker.sh
  rm -f /tmp/get-docker.sh
fi

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

if [[ ! -t 0 ]]; then
  exec </dev/tty
fi

API_ENV="$APP_DIR/telegram-bot-api.env"
if [[ ! -f "$API_ENV" ]]; then
  TELEGRAM_API_ID=""
  TELEGRAM_API_HASH=""
  echo "Для файлов до 2000 МБ нужны api_id и api_hash с https://my.telegram.org/apps"
  while [[ ! "$TELEGRAM_API_ID" =~ ^[0-9]+$ ]]; do
    read -r -p "Telegram API ID (только цифры): " TELEGRAM_API_ID || TELEGRAM_API_ID=""
  done
  while [[ -z "$TELEGRAM_API_HASH" ]]; do
    read -r -s -p "Telegram API Hash (ввод скрыт): " TELEGRAM_API_HASH || TELEGRAM_API_HASH=""
    echo
  done
  printf 'TELEGRAM_API_ID=%s\nTELEGRAM_API_HASH=%s\n' "$TELEGRAM_API_ID" "$TELEGRAM_API_HASH" > "$API_ENV"
  chmod 600 "$API_ENV"
fi

install -d -m 750 /var/lib/snatchvideo-bot /var/lib/snatchvideo-bot/tmp /var/lib/telegram-bot-api

cat > /etc/systemd/system/telegram-bot-api.service <<EOF
[Unit]
Description=Local Telegram Bot API
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=simple
EnvironmentFile=$API_ENV
ExecStartPre=-/usr/bin/docker rm -f snatchvideo-telegram-bot-api
# Только loopback: 127.0.0.1:8081:8081
ExecStart=/usr/bin/docker run --name snatchvideo-telegram-bot-api --rm --network host \
  -v /var/lib/telegram-bot-api:/var/lib/telegram-bot-api \
  aiogram/telegram-bot-api:latest \
  --api-id=\${TELEGRAM_API_ID} --api-hash=\${TELEGRAM_API_HASH} \
  --http-ip-address=127.0.0.1 --http-port=8081 --local \
  --dir=/var/lib/telegram-bot-api --temp-dir=/var/lib/telegram-bot-api/tmp
ExecStop=/usr/bin/docker stop snatchvideo-telegram-bot-api
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

python3 - "$APP_DIR/.env" <<'PY'
from pathlib import Path

path = Path(__import__('sys').argv[1])
values = {
    'USE_LOCAL_BOT_API': 'true',
    'TELEGRAM_API_BASE': 'http://127.0.0.1:8081',
    'MAX_FILE_SIZE_MB': '2000',
}
lines = path.read_text().splitlines()
seen = set()
for index, line in enumerate(lines):
    key = line.split('=', 1)[0] if '=' in line else ''
    if key in values:
        lines[index] = f'{key}={values[key]}'
        seen.add(key)
for key, value in values.items():
    if key not in seen:
        lines.append(f'{key}={value}')
path.write_text('\n'.join(lines) + '\n')
PY
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
systemctl enable docker telegram-bot-api.service "$SERVICE_NAME"
systemctl restart docker telegram-bot-api.service
for _ in {1..30}; do
  if curl -fsS http://127.0.0.1:8081 >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! curl -fsS http://127.0.0.1:8081 >/dev/null 2>&1; then
  journalctl -u telegram-bot-api.service -n 100 --no-pager
  exit 1
fi
systemctl restart "$SERVICE_NAME"
sleep 3
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  journalctl -u "$SERVICE_NAME" -n 100 --no-pager
  exit 1
fi

printf '\nSnatchVideo Bot установлен и запущен.\nСтатус: systemctl status %s\nЛоги: journalctl -u %s -f\nОбновление: повторите ту же команду установки.\n' "$SERVICE_NAME" "$SERVICE_NAME"
