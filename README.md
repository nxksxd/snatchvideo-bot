# SnatchVideo Bot

Telegram-бот для скачивания видео и аудио по ссылке. Поддерживает выбор качества, ведёт статистику, ограничивает параллельные загрузки и автоматически удаляет временные файлы.

## Поддерживаемые сервисы

- YouTube и `youtu.be`
- Rutube
- VK Video: `vk.com`, `vk.ru`, `vkvideo.ru`
- Instagram
- TikTok, включая короткие ссылки `vm.tiktok.com` и `vt.tiktok.com`

Фактическая доступность отдельных роликов зависит от ограничений платформы, региона VPS, cookies и версии `yt-dlp`.

## Функционал

- Скачивание видео по ссылке.
- Выбор качества: 1080p, 720p, 480p или 360p.
- Извлечение и отправка аудио.
- Информация о ролике до скачивания.
- Ограничение количества одновременных загрузок.
- Отмена активной задачи через `/cancel`.
- Автоматическая очистка временных файлов.
- Повторные попытки отправки в Telegram.
- Совместимость видео с Telegram и iOS через FFmpeg.
- Личная статистика пользователя.
- Общая статистика для администратора.
- SQLite в режиме WAL с `busy_timeout`.
- Опциональный SOCKS5-прокси для Rutube.
- Опциональные cookies для YouTube и Instagram.
- Поддержка self-hosted Telegram Bot API для больших файлов.
- Автозапуск и восстановление после сбоя через systemd.

## Команды бота

- `/start` — открыть бота.
- `/mystats` — показать личную статистику.
- `/stats` — общая статистика, доступна администратору.
- `/cancel` — отменить текущую загрузку.
- `/restart` — перезапустить сценарий работы.

## Stack

- Python 3.10+
- aiogram 3 — Telegram Bot API и FSM.
- yt-dlp — получение метаданных и скачивание медиа.
- FFmpeg и FFprobe — объединение потоков, аудио и совместимость видео.
- Deno — выполнение JavaScript-компонентов yt-dlp для YouTube.
- SQLite — статистика пользователей и загрузок.
- python-dotenv — конфигурация через `.env`.
- asyncio — асинхронная обработка и контроль параллелизма.
- systemd — production-запуск на VPS.

## Требования к VPS

Поддерживаются Ubuntu 22.04/24.04 и актуальные Debian.

Для небольшого бота:

- 2 vCPU;
- 2–4 ГБ RAM;
- 40–100 ГБ SSD/NVMe;
- канал от 500 Мбит/с;
- достаточный месячный лимит трафика.

Для нескольких параллельных крупных загрузок лучше 4 vCPU, 8 ГБ RAM, NVMe и канал 1 Гбит/с.

## Подготовка VPS

Подключитесь к новому серверу по SSH. Для установки достаточно пользователя с `sudo`.

Убедитесь, что исходящие подключения к Telegram и видеосервисам разрешены. Отдельно устанавливать Python, FFmpeg, Deno или зависимости не требуется — установщик сделает это сам.

Создайте бота через [@BotFather](https://t.me/BotFather) и узнайте свой числовой Telegram ID. Токен не публикуйте в GitHub и не отправляйте посторонним.

## Установка одной командой

```bash
curl -fsSL https://raw.githubusercontent.com/nxksxd/snatchvideo-bot/main/install.sh | sudo bash
```

Установщик запросит:

1. Telegram Bot Token от `@BotFather` — ввод скрыт.
2. Ваш Telegram ID для `ADMIN_ID`.
3. Telegram `api_id` и `api_hash` с [my.telegram.org/apps](https://my.telegram.org/apps) — нужны локальному Bot API для отправки файлов до 2000 МБ. `api_hash` вводится скрыто.

`api_id` и `api_hash` создаются один раз: войдите на `my.telegram.org`, откройте `API development tools`, создайте приложение с любым названием и скопируйте значения непосредственно в терминал VPS. Не отправляйте `api_hash` в чат и не публикуйте его.

Затем он автоматически:

- установит системные зависимости;
- установит Deno;
- скачает актуальную версию `main` в `/opt/snatchvideo-bot`;
- создаст Python virtual environment;
- установит зависимости;
- создаст защищённый `.env` с правами `600`;
- создаст systemd-сервис;
- запустит бота и проверит его состояние.

Повторный запуск той же команды обновляет код до актуального `main`, переустанавливает зависимости и перезапускает сервис. Существующие `.env` и статистика сохраняются.

## Управление на VPS

Статус:

```bash
sudo systemctl status snatchvideo-bot
```

Логи:

```bash
sudo journalctl -u snatchvideo-bot -f
```

Перезапуск:

```bash
sudo systemctl restart snatchvideo-bot
```

Остановка и запуск:

```bash
sudo systemctl stop snatchvideo-bot
sudo systemctl start snatchvideo-bot
```

Обновление:

```bash
curl -fsSL https://raw.githubusercontent.com/nxksxd/snatchvideo-bot/main/install.sh | sudo bash
```

## Настройка

Конфигурация хранится на VPS:

```text
/opt/snatchvideo-bot/.env
```

После изменения выполните:

```bash
sudo systemctl restart snatchvideo-bot
```

Основные параметры:

- `TELEGRAM_BOT_TOKEN` — обязательный токен бота.
- `ADMIN_ID` — Telegram ID администратора.
- `MAX_FILE_SIZE_MB` — максимальный размер файла.
- `DOWNLOAD_TIMEOUT` — тайм-аут загрузки в секундах.
- `DOWNLOAD_SEMAPHORE_LIMIT` — число параллельных загрузок.
- `RUTUBE_PROXY` — необязательный SOCKS5-прокси.
- `YOUTUBE_COOKIES_FILE` — путь к cookies YouTube.
- `INSTAGRAM_COOKIES_FILE` — путь к cookies Instagram.
- `USE_LOCAL_BOT_API` — использование локального Telegram Bot API.
- `TELEGRAM_API_BASE` — адрес локального Bot API.

## Cookies YouTube и Instagram

Датацентровые IP часто получают антибот-проверки. Для стабильной работы используйте cookies только от отдельных технических аккаунтов.

Cookies дают полный доступ к сессии аккаунта. Не используйте основной аккаунт, не коммитьте файлы и установите права `600`.

Пример:

```bash
sudo install -d -m 700 /opt/snatchvideo-bot/secrets
sudo install -m 600 youtube-cookies.txt /opt/snatchvideo-bot/secrets/youtube.txt
sudo install -m 600 instagram-cookies.txt /opt/snatchvideo-bot/secrets/instagram.txt
sudo nano /opt/snatchvideo-bot/.env
```

Укажите:

```env
YOUTUBE_COOKIES_FILE=/opt/snatchvideo-bot/secrets/youtube.txt
INSTAGRAM_COOKIES_FILE=/opt/snatchvideo-bot/secrets/instagram.txt
```

Затем перезапустите сервис.

## Ограничение Telegram по размеру файлов

Официальный Telegram Bot API ограничивает отправку больших файлов. Значение `MAX_FILE_SIZE_MB=2000` само по себе не отменяет лимит API.

Установщик автоматически запускает self-hosted `telegram-bot-api` в отдельном Docker-контейнере, привязанном только к `127.0.0.1:8081`, и выставляет:

```env
USE_LOCAL_BOT_API=true
TELEGRAM_API_BASE=http://127.0.0.1:8081
MAX_FILE_SIZE_MB=2000
```

Данные локального API хранятся в `/var/lib/telegram-bot-api`, а его секреты — в `/opt/snatchvideo-bot/telegram-bot-api.env` с правами `600`.

Проверка:

```bash
sudo systemctl status telegram-bot-api snatchvideo-bot
sudo journalctl -u telegram-bot-api -n 50 --no-pager
```

Без локального Bot API уменьшите `MAX_FILE_SIZE_MB` до значения, которое принимает официальный API.

## Локальная разработка

```bash
git clone https://github.com/nxksxd/snatchvideo-bot.git
cd snatchvideo-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

Тесты:

```bash
python -m unittest discover -s tests
```

## Структура проекта

```text
bot.py                 точка входа
settings.py            чтение и проверка настроек
handlers/              команды, ссылки и callback-запросы
services/downloader.py yt-dlp и управление загрузками
services/sender.py     отправка файлов в Telegram
services/cleanup.py    очистка временных файлов
repositories/          SQLite-репозитории
models/                модели задач
install.sh             установка и обновление VPS
TROUBLESHOOTING.md     диагностика частых проблем
```

## Безопасность

- `.env`, cookies, базы и ключи исключены через `.gitignore`.
- Никогда не коммитьте токен Telegram и cookies.
- При утечке токена немедленно перевыпустите его через `@BotFather`.
- Cookies при утечке нужно отозвать завершением соответствующей сессии аккаунта.

Используйте бот только для материалов, которые вам разрешено скачивать, и соблюдайте условия используемых платформ и применимое законодательство.
