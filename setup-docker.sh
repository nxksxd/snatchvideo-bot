#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/snatchvideo-bot
cd "$APP_DIR"

if [[ ! -t 0 ]]; then
  echo "Запустите скрипт непосредственно в терминале: sudo ./setup-docker.sh" >&2
  exit 1
fi

BOT_TOKEN=""
ADMIN_ID=""
API_ID=""
API_HASH=""

while [[ -z "$BOT_TOKEN" ]]; do
  read -r -s -p "Telegram Bot Token от @BotFather: " BOT_TOKEN
  echo
 done
while [[ ! "$ADMIN_ID" =~ ^[0-9]+$ ]]; do
  read -r -p "Telegram ID администратора (только цифры): " ADMIN_ID
 done
while [[ ! "$API_ID" =~ ^[0-9]+$ ]]; do
  read -r -p "Telegram API ID с my.telegram.org (только цифры): " API_ID
 done
while [[ -z "$API_HASH" ]]; do
  read -r -s -p "Telegram API Hash с my.telegram.org: " API_HASH
  echo
 done

umask 077
printf '%s\n' \
  "TELEGRAM_BOT_TOKEN=$BOT_TOKEN" \
  "ADMIN_ID=$ADMIN_ID" \
  "LOG_LEVEL=INFO" \
  > .env
printf '%s\n' \
  "TELEGRAM_API_ID=$API_ID" \
  "TELEGRAM_API_HASH=$API_HASH" \
  "TELEGRAM_HTTP_PORT=8081" \
  "TELEGRAM_LOCAL=1" \
  > telegram-bot-api.env
chmod 600 .env telegram-bot-api.env
unset BOT_TOKEN API_HASH

mkdir -p secrets
docker compose config --quiet
echo "Секреты сохранены. Контейнеры ещё не запущены."
