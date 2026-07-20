# SnatchVideo Bot

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.26-2CA5E0?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![yt--dlp](https://img.shields.io/badge/yt--dlp-2026.03-red)](https://github.com/yt-dlp/yt-dlp)
[![Telegram Bot API](https://img.shields.io/badge/Telegram_Bot_API-local-26A5E4?logo=telegram&logoColor=white)](https://github.com/tdlib/telegram-bot-api)

Production-ready Telegram-бот для скачивания видео и аудио по ссылке. Поддерживает выбор качества, файлы до 2000 МБ через локальный Telegram Bot API, статистику, ограничение параллельных задач и автоматическую очистку временных данных.

## Навигация

- [Возможности](#функционал)
- [Поддерживаемые сервисы](#поддерживаемые-сервисы)
- [Технологический стек](#технологический-стек)
- [Архитектура](#архитектура)
- [Требования к VPS](#требования-к-vps)
- [Подробная установка](#подробная-установка-на-vps)
- [Управление на VPS](#управление-на-vps)
- [Настройка](#настройка)
- [Безопасность](#безопасность)

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

## Технологический стек

### Приложение

| Технология | Роль в проекте |
|---|---|
| Python 3.10+ | Основной язык приложения и асинхронной бизнес-логики. |
| aiogram 3.26 | Telegram-команды, сообщения, callback-кнопки, FSM и polling. |
| asyncio | Параллельная обработка пользователей, загрузок и фоновой очистки без блокировки бота. |
| Pydantic | Проверка и типизация данных, используемых aiogram. |
| python-dotenv | Загрузка настроек и секретов из `.env`. |

### Медиа

| Технология | Роль в проекте |
|---|---|
| yt-dlp | Получение метаданных, доступных форматов и скачивание видео/аудио с поддерживаемых платформ. |
| FFmpeg | Объединение видео- и аудиопотоков, извлечение MP3, создание превью и перекодирование. |
| FFprobe | Анализ кодеков, разрешения и совместимости готового файла с Telegram и iOS. |
| Deno | JavaScript runtime для современных YouTube-проверок и EJS-компонентов yt-dlp. |

### Данные и инфраструктура

| Технология | Роль в проекте |
|---|---|
| SQLite WAL | Локальная статистика пользователей и загрузок с `busy_timeout` для конкурентного доступа. |
| Local Telegram Bot API | Self-hosted API для отправки файлов до 2000 МБ вместо лимита официального API. |
| Docker | Изолированный запуск локального `telegram-bot-api` без сборки TDLib вручную. |
| systemd | Автозапуск, перезапуск после сбоя и управление ботом и локальным API. |
| Bash | Повторяемая установка и обновление VPS одной командой. |
| Git/GitHub | Доставка актуальной ветки `main` на сервер. |

### Тестирование

Проект использует стандартный `unittest`. Тесты проверяют обработчики, маршрутизацию, скачивание, cookies, оценку размера, совместимость медиа, повторы Telegram API, SQLite и контракт production-установщика.

```bash
python -m unittest discover -s tests
```

## Архитектура

```text
Пользователь Telegram
        │
        ▼
Local Telegram Bot API :8081
        │
        ▼
aiogram Dispatcher ──► handlers/
        │                    │
        │                    ├── команды и FSM
        │                    ├── выбор качества
        │                    └── прогресс и отмена
        ▼
DownloadManager ──► yt-dlp ──► Deno/EJS
        │
        ▼
FFmpeg / FFprobe
        │
        ├──► временные файлы /var/lib/snatchvideo-bot/tmp
        ├──► SQLite /var/lib/snatchvideo-bot/stats.db
        └──► отправка готового файла через Local Bot API
```

Основные принципы:

- бот работает через long polling и не требует публичного HTTP-порта;
- локальный Telegram Bot API доступен только на `127.0.0.1:8081`;
- одному пользователю разрешена одна активная загрузка;
- общий параллелизм регулируется `DOWNLOAD_SEMAPHORE_LIMIT`;
- временные каталоги привязаны к `job_id` и удаляются после завершения или по TTL;
- SQLite хранит статистику отдельно от временных медиа;
- два независимых systemd-сервиса позволяют перезапускать бот и локальный API отдельно.

## Требования к VPS

Поддерживаются Ubuntu 22.04/24.04 и актуальные Debian.

Для небольшого бота:

- 2 vCPU;
- 2–4 ГБ RAM;
- 40–100 ГБ SSD/NVMe;
- канал от 500 Мбит/с;
- достаточный месячный лимит трафика.

Такая конфигурация рассчитана примерно на 2–3 одновременные загрузки обычных роликов в качестве до 720p. Если FFmpeg перекодирует видео, комфортная нагрузка снижается до 1–2 одновременных задач, поскольку перекодирование активно использует CPU и временно требует дополнительное место на диске.

Для нескольких параллельных крупных загрузок лучше 4 vCPU, 8 ГБ RAM, NVMe и канал 1 Гбит/с. Ориентировочно такой сервер выдержит 5–8 одновременных загрузок без перекодирования или 2–4 задачи с активным FFmpeg. Для файлов размером 1–2 ГБ безопаснее ограничиться 2–3 параллельными задачами, чтобы одновременно хватало диска на исходные потоки, объединённый файл и отправку через Telegram.

Фактическое количество зависит от размера и качества видео, скорости видеохостинга, необходимости перекодирования, пропускной способности VPS и скорости загрузки в Telegram. По умолчанию бот ограничивает работу параметром `DOWNLOAD_SEMAPHORE_LIMIT=3`; увеличивайте его постепенно, контролируя CPU, RAM, свободное место и канал.

## Подробная установка на VPS

### 1. Подготовьте сервер

Поддерживаются Ubuntu 22.04/24.04 и актуальные Debian. Подключитесь по SSH под `root` или пользователем с доступом к `sudo`.

Убедитесь, что сервер имеет доступ к GitHub, Telegram и нужным видеосервисам. Python, FFmpeg, Deno, Docker и Python-зависимости установщик проверит и при необходимости установит автоматически.

### 2. Создайте Telegram-бота и получите Bot Token

1. Откройте официальный бот [@BotFather](https://t.me/BotFather) в Telegram.
2. Отправьте команду `/newbot`.
3. Укажите отображаемое имя бота.
4. Укажите уникальное имя пользователя, которое заканчивается на `bot`, например `my_video_loader_bot`.
5. BotFather пришлёт токен вида `1234567890:AA...`. Это значение понадобится установщику как `Telegram Bot Token`.
6. Откройте созданного бота и нажмите `Start` или отправьте `/start`. Без этого бот не сможет первым прислать администратору уведомление об успешном запуске.

Bot Token даёт полный контроль над ботом. Не вставляйте его в README, GitHub, чат, скриншоты или команды shell. Вводите токен только в скрытом приглашении установщика. При утечке выполните `/revoke` в BotFather и получите новый токен.

### 3. Узнайте свой Telegram ID

Установщику нужен числовой ID администратора, а не `@username`.

Откройте в Telegram бота [@userinfobot](https://t.me/userinfobot) или аналогичный сервис определения ID и скопируйте значение `Id`, например `448795617`. В установщик вводите только цифры, без `@`, пробелов и скобок.

Этот ID используется для команды `/stats` и для личного уведомления об успешном запуске.

### 4. Получите Telegram API ID и API Hash

`Telegram API ID` и `Telegram API Hash` — это не Bot Token. Они относятся к приложению Telegram API и нужны локальному серверу `telegram-bot-api`, чтобы бот мог отправлять файлы размером до 2000 МБ.

1. Откройте [https://my.telegram.org](https://my.telegram.org) в браузере.
2. Введите номер телефона аккаунта Telegram в международном формате, например `+79991234567`.
3. Код подтверждения обычно приходит в официальный клиент Telegram, а не по SMS. Введите его на сайте.
4. Откройте раздел [API development tools](https://my.telegram.org/apps).
5. Если приложение ещё не создано, заполните форму:
   - `App title` — любое понятное название, например `SnatchVideo Bot`;
   - `Short name` — короткое имя латиницей без пробелов, например `snatchvideo`;
   - `Platform` — можно выбрать `Desktop` или `Other`;
   - `Description` — необязательное краткое описание.
6. Нажмите `Create application`.
7. На странице приложения найдите:
   - `App api_id` — числовое значение, его введите в приглашение `Telegram API ID`;
   - `App api_hash` — строка из букв и цифр, её введите в приглашение `Telegram API Hash`.

`api_hash` является секретом. Не отправляйте его в чат, не публикуйте в GitHub и не показывайте на скриншотах. При вводе `Telegram API Hash` терминал ничего не отображает — это нормальный скрытый ввод. Вставьте значение и нажмите Enter.

Одни `api_id/api_hash` можно использовать для повторной установки этого бота на том же сервере. После первой установки они сохраняются в `/opt/snatchvideo-bot/telegram-bot-api.env` с правами `600` и повторно не запрашиваются.

### 5. Запустите установщик

```bash
curl -fsSL "https://raw.githubusercontent.com/nxksxd/snatchvideo-bot/main/install.sh?$(date +%s)" | sudo bash
```

Параметр с датой предотвращает получение старой версии установщика из HTTP-кэша.

При первой установке последовательно введите:

1. `Telegram Bot Token от @BotFather` — ввод скрыт;
2. `Ваш Telegram ID (ADMIN_ID)` — только цифры;
3. `Telegram API ID` — только цифры;
4. `Telegram API Hash` — ввод скрыт.

Установщик автоматически:

- проверит и установит системные зависимости;
- установит Deno без интерактивных вопросов;
- скачает актуальную ветку `main` в `/opt/snatchvideo-bot`;
- создаст Python virtual environment и установит зависимости;
- сохранит конфигурацию бота в `/opt/snatchvideo-bot/.env` с правами `600`;
- запустит локальный Telegram Bot API в отдельном Docker-контейнере;
- привяжет локальный API только к `127.0.0.1:8081`;
- выставит лимит `MAX_FILE_SIZE_MB=2000`;
- создаст и включит systemd-сервисы `telegram-bot-api` и `snatchvideo-bot`;
- проверит готовность локального API и запуск бота;
- отправит сообщение об успешном запуске только указанному администратору.

Успешное завершение содержит строку `SnatchVideo Bot установлен и запущен.`

### 6. Проверьте установку

```bash
sudo systemctl status telegram-bot-api snatchvideo-bot --no-pager
```

Оба сервиса должны иметь статус `active (running)`.

Проверьте последние логи:

```bash
sudo journalctl -u telegram-bot-api -n 50 --no-pager
sudo journalctl -u snatchvideo-bot -n 50 --no-pager
```

Откройте бота в Telegram, отправьте `/start`, затем ссылку на видео и выберите качество. Для проверки локального API используйте файл крупнее 50 МБ, но меньше 2000 МБ.

### 7. Повторная установка и обновление

Та же команда обновляет проект до актуальной версии `main` и перезапускает сервисы:

```bash
curl -fsSL "https://raw.githubusercontent.com/nxksxd/snatchvideo-bot/main/install.sh?$(date +%s)" | sudo bash
```

Существующие Bot Token, ADMIN_ID, Telegram API ID/API Hash и база статистики сохраняются. Удалять Docker, контейнеры или `/opt/snatchvideo-bot` перед обновлением не нужно.

### Частые проблемы установки

- После `Telegram API Hash` символы не появляются — ввод скрыт, вставьте значение и нажмите Enter.
- `containerd.io: Conflicts: containerd` — используйте актуальный установщик: он переиспользует существующий Docker CE и не ставит конфликтующий `docker.io`.
- Установка остановилась после Python-зависимостей — убедитесь, что используется актуальная команда с `?$(date +%s)`, затем остановите старый процесс через `Ctrl+C` и повторите запуск.
- Долго отображается `Запуск локального Telegram Bot API` — при первом запуске Docker скачивает образ; проверьте `sudo journalctl -u telegram-bot-api -n 100 --no-pager`.
- `TelegramNotFound: Not Found` — неверный или отозванный Bot Token. Получите новый токен через BotFather.
- `Request Entity Too Large` — бот использует официальный API вместо локального. Проверьте `USE_LOCAL_BOT_API=true`, `TELEGRAM_API_BASE=http://127.0.0.1:8081` и статус `telegram-bot-api`.

Повторно вводить секреты в команды shell не нужно. Для диагностики не публикуйте содержимое `.env` и `telegram-bot-api.env`.

## Управление на VPS

| Действие | Команда |
|---|---|
| Статус обоих сервисов | `sudo systemctl status telegram-bot-api snatchvideo-bot --no-pager` |
| Логи бота в реальном времени | `sudo journalctl -u snatchvideo-bot -f` |
| Логи локального Bot API | `sudo journalctl -u telegram-bot-api -f` |
| Перезапуск бота | `sudo systemctl restart snatchvideo-bot` |
| Перезапуск локального API | `sudo systemctl restart telegram-bot-api` |
| Остановка бота | `sudo systemctl stop snatchvideo-bot` |
| Запуск бота | `sudo systemctl start snatchvideo-bot` |

Обновление до актуальной версии:

```bash
curl -fsSL "https://raw.githubusercontent.com/nxksxd/snatchvideo-bot/main/install.sh?$(date +%s)" | sudo bash
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
