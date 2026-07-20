## Решение ошибки "Unable to handle request"

Эта ошибка возникает когда yt-dlp не может получить информацию о видео.

### 🔧 Шаг 1: Проверьте yt-dlp напрямую

Из директории проекта:

```bash
# Запустите тест с YouTube ссылкой
python test_yt_dlp.py "https://www.youtube.com/watch?v=..."

# Или так (вас попросит ввести URL)
python test_yt_dlp.py
```

Это покажет точную ошибку yt-dlp.

### 🔍 Шаг 2: Возможные причины

| Проблема | Решение |
|----------|---------|
| yt-dlp устарел | `pip install --upgrade yt-dlp` |
| YouTube изменил API | Обновить yt-dlp (см. выше) |
| Нет интернета / блокировка | Проверьте соединение |
| Видео недоступно | Попробуйте другое видео |
| Возраст видео | YouTube требует авторизацию - проверьте в браузере |

### 📝 Шаг 3: Обновление yt-dlp

```bash
# Полное переустановление
pip uninstall yt-dlp -y
pip install yt-dlp

# Проверка версии
yt-dlp --version
```

### 📊 Шаг 4: Просмотр логов бота

Логи показывают подробную информацию об ошибке. Запустите бота и посмотрите консоль:

```bash
python bot.py
```

Найдите строку "❌ Ошибка extract_info:" - там будет точное описание проблемы.

### ✅ Шаг 5: Проверка конфигурации

Убедитесь, что заполнен `.env` и при необходимости включен локальный Bot API:

```env
TELEGRAM_BOT_TOKEN=your_token
USE_LOCAL_BOT_API=false
TELEGRAM_API_BASE=http://localhost:8081
```

Если используете локальный Bot API, проверьте что сервис доступен:

```bash
curl http://localhost:8081
```

### 🎥 YouTube: "Sign in to confirm you're not a bot" / только storyboards

YouTube активно борется со скачиванием с датацентр-IP. Симптомы:

- `ERROR: [youtube] <id>: Sign in to confirm you're not a bot.`
- В `--list-formats` видны только `sb0…sb3` (storyboards), нет реальных форматов.
- Предупреждение `Some web client https formats have been skipped … YouTube is forcing SABR streaming` (https://github.com/yt-dlp/yt-dlp/issues/12482).

Что использует бот для YouTube (`services/downloader.py`):

1. **`player_client=tv_embedded`** — yt-dlp 2026.3+ деградирует его в `android_vr` (без cookies) или `tv downgraded` / `web_safari` (с cookies). Оба пути не подвержены SABR.
2. **`remote_components=ejs:github`** — разрешает yt-dlp скачать EJS-челлендж-солвер с GitHub. Без него `n challenge solving failed: Some formats may be missing`, в ответе только storyboards. После первого запуска скрипт кешируется.
3. **`cookiefile=...`** (`YOUTUBE_COOKIES_FILE` в `.env`) — экспорт cookies от выделенного бот-аккаунта Google в Netscape-формате. Без cookies «Sign in to confirm you're not a bot» возвращается даже для популярных видео.
4. **`deno`** — JS-runtime для самого решателя. Проверь `deno --version` (должен быть `≥ 2.x`).

Все 4 условия должны выполняться одновременно. Если убрать хотя бы одно — YouTube падает.

Что точно НЕ помогает:

- Принудительный `player_client=web/web_safari/mweb/ios` без EJS-солвера — все они либо требуют PO Token, либо уходят в SABR.
- Цепочка `default,web,mweb,ios,…` без cookies/ejs — то же самое.
- Просто новая версия yt-dlp без `--remote-components ejs:github`.

Если конкретное видео не качается даже с правильными настройками — скорее всего age-restricted / private / region-locked. В этом случае нужен PO Token plugin (https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) — он в боте не настроен.

### 📱 Instagram: "Requested content is not available, rate-limit reached or login required"

Instagram на датацентр-IP не отдаёт reels/stories анонимно — webpage сразу редиректит на login. yt-dlp пытается embed-страницу и тоже упирается в стену:

- `WARNING: [Instagram] Main webpage is locked behind the login page`
- `ERROR: [Instagram] <id>: Requested content is not available, rate-limit reached or login required.`

Решение — задать `INSTAGRAM_COOKIES_FILE` в `.env`, указывающий на cookies-файл от **выделенного** бот-аккаунта Instagram (не свой основной). Шаги:

1. Завести отдельный аккаунт Instagram. Залогиниться, посмотреть пару reels (для «прогрева» сессии).
2. Поставить расширение «Get cookies.txt LOCALLY» (Chrome) или «cookies.txt» (Firefox).
3. На странице `instagram.com` экспортировать cookies в Netscape-формате (`# Netscape HTTP Cookie File` в начале).
4. Положить файл на сервер с `chmod 600`, например `/opt/snatchvideo-bot/secrets/instagram.txt`.
5. Прописать `INSTAGRAM_COOKIES_FILE=/opt/snatchvideo-bot/secrets/instagram.txt` в `.env` и перезапустить сервис.

В стартовом логе появится строка `🍪 Instagram cookies: ... (ok)`. Дальше большинство публичных reels должны качаться.

Cookies для Instagram периодически устаревают (обычно несколько недель–месяцев). Если внезапно опять появляется ошибка login required — переэкспортируй cookies.

### 🆘 Если ничего не помогло

Соберите информацию:
1. Запустите `python test_yt_dlp.py` с проблемной ссылкой
2. Скопируйте полный текст ошибки
3. Проверьте версию: `yt-dlp --version` и `pip list | grep -i yt`
4. Попробуйте на другие источники (YouTube, Rutube, VK)
5. Убедитесь, что `ffmpeg -version` отрабатывает без ошибки
