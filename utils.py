"""
Вспомогательные функции для работы с URL, форматирования и т.д.
"""

import re
from urllib.parse import urlparse
from html import escape
from typing import Dict, Optional, List

import config


# ─── Константы ──────────────────────────────────────────────────────────────
URL_PATTERN = re.compile(
    r'^(https?://)?(www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/|$)',
    re.IGNORECASE
)

EMOJI_MAP = {
    'video': '🎬',
    'audio': '🎵',
}


# ─── Проверка URL ───────────────────────────────────────────────────────────

def is_url(text: str) -> bool:
    """Проверяет, является ли текст URL."""
    return bool(URL_PATTERN.match(text.strip()))


def normalize_url(text: str) -> str:
    """Добавляет схему https://, если пользователь отправил ссылку без неё."""
    value = text.strip()
    if value and not value.startswith(("http://", "https://")):
        return f"https://{value}"
    return value


def is_supported_url(url: str) -> bool:
    """Проверяет, поддерживается ли домен видеохостинга."""
    domain = urlparse(url).netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    return any(domain == d or domain.endswith('.' + d) for d in config.SUPPORTED_VIDEO_DOMAINS)


def is_rutube_url(url: str) -> bool:
    """Проверяет, является ли URL ссылкой на Rutube."""
    domain = urlparse(url).netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain == 'rutube.ru' or domain.endswith('.rutube.ru')


def is_youtube_url(url: str) -> bool:
    """Проверяет, является ли URL ссылкой на YouTube."""
    domain = urlparse(url).netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain in ('youtube.com', 'youtu.be', 'm.youtube.com', 'music.youtube.com')


def is_instagram_url(url: str) -> bool:
    """Проверяет, является ли URL ссылкой на Instagram."""
    domain = urlparse(url).netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain == 'instagram.com'


def is_tiktok_url(url: str) -> bool:
    """Проверяет, является ли URL ссылкой на TikTok."""
    domain = urlparse(url).netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain in ('tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com')


def get_domain_label(url: str) -> str:
    """Возвращает читаемое имя площадки по URL."""
    domain = urlparse(url).netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]

    if 'youtube.com' in domain or 'youtu.be' in domain:
        return 'YouTube'
    elif 'rutube.ru' in domain:
        return 'Rutube'
    elif 'vk.com' in domain or 'vk.ru' in domain or 'vkvideo.ru' in domain:
        return 'VK'
    elif 'instagram.com' in domain:
        return 'Instagram'
    elif 'tiktok.com' in domain or 'vm.tiktok.com' in domain or 'vt.tiktok.com' in domain:
        return 'TikTok'
    return domain


# ─── Форматирование ─────────────────────────────────────────────────────────

def format_bytes(b: int) -> str:
    """Форматирует байты в читаемый вид."""
    if b < 1024:
        return f"{b} Б"
    elif b < 1024 ** 2:
        return f"{b / 1024:.1f} КБ"
    elif b < 1024 ** 3:
        return f"{b / 1024 ** 2:.1f} МБ"
    else:
        return f"{b / 1024 ** 3:.2f} ГБ"


def get_bar(pct: float) -> str:
    """Возвращает мини-бар из эмодзи для визуализации процентов."""
    filled = round(pct / 10)
    return '▓' * filled + '░' * (10 - filled)


def safe_error(e: Exception) -> str:
    """Безопасно конвертирует исключение в строку с экранированием HTML."""
    return escape(str(e))


def escape_html(text: str) -> str:
    """Экранирует пользовательский текст для HTML."""
    return escape(text)


def format_global_stats(stats: Dict) -> str:
    """Форматирует общую статистику в читаемый текст."""
    lines = []
    lines.append("📊 <b>Общая статистика бота</b>\n")

    lines.append(f"📥 Всего загрузок: <b>{stats['total_downloads']}</b>")
    lines.append(f"👥 Уникальных пользователей: <b>{stats['unique_users']}</b>")
    lines.append(f"💾 Общий объём: <b>{format_bytes(stats['total_bytes'])}</b>")
    lines.append("")

    lines.append("📅 <b>По периодам:</b>")
    lines.append(f"  • Сегодня: <b>{stats['today_downloads']}</b>")
    lines.append(f"  • За 7 дней: <b>{stats['week_downloads']}</b>")
    lines.append(f"  • За 30 дней: <b>{stats['month_downloads']}</b>")
    lines.append("")

    if stats['by_domain']:
        lines.append("🌐 <b>По площадкам:</b>")
        for domain, cnt in stats['by_domain']:
            pct = (cnt / stats['total_downloads'] * 100) if stats['total_downloads'] else 0
            bar = get_bar(pct)
            lines.append(f"  {bar} {domain}: <b>{cnt}</b> ({pct:.1f}%)")
        lines.append("")

    if stats['by_type']:
        lines.append("📁 <b>По типу:</b>")
        for media_type, cnt in stats['by_type']:
            emoji = EMOJI_MAP.get(media_type, '📦')
            lines.append(f"  {emoji} {media_type}: <b>{cnt}</b>")
        lines.append("")

    if stats['by_quality']:
        lines.append("📐 <b>Популярные качества (видео):</b>")
        for quality, cnt in stats['by_quality']:
            lines.append(f"  • {quality}p: <b>{cnt}</b>")
        lines.append("")

    if stats['top_users']:
        lines.append("🏆 <b>Топ-10 пользователей:</b>")
        for i, (uid, uname, fname, lname, cnt) in enumerate(stats['top_users'], 1):
            medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, f'{i}.')
            display = uname if uname else (fname or str(uid))
            lines.append(
                f"  {medal} @{display}: <b>{cnt}</b>" if uname
                else f"  {medal} {display}: <b>{cnt}</b>"
            )

    return '\n'.join(lines)


def format_user_stats(stats: Dict) -> str:
    """Форматирует личную статистику пользователя."""
    if stats['total'] == 0:
        return "📊 У вас пока нет загрузок. Отправьте ссылку на видео! 🎬"

    lines = []
    lines.append("📊 <b>Ваша статистика</b>\n")

    lines.append(f"📥 Всего загрузок: <b>{stats['total']}</b>")
    lines.append(f"💾 Общий объём: <b>{format_bytes(stats['total_bytes'])}</b>")
    lines.append("")

    if stats['by_domain']:
        lines.append("🌐 <b>По площадкам:</b>")
        for domain, cnt in stats['by_domain']:
            pct = (cnt / stats['total'] * 100) if stats['total'] else 0
            bar = get_bar(pct)
            lines.append(f"  {bar} {domain}: <b>{cnt}</b> ({pct:.1f}%)")
        lines.append("")

    if stats['by_type']:
        lines.append("📁 <b>По типу:</b>")
        for media_type, cnt in stats['by_type']:
            emoji = EMOJI_MAP.get(media_type, '📦')
            lines.append(f"  {emoji} {media_type}: <b>{cnt}</b>")
        lines.append("")

    if stats['first_download']:
        lines.append(f"📅 Первая загрузка: <b>{stats['first_download']}</b>")
    if stats['last_download']:
        lines.append(f"📅 Последняя загрузка: <b>{stats['last_download']}</b>")

    return '\n'.join(lines)


def build_quality_keyboard(
    sorted_qualities: List[str],
    quality_sizes: Optional[Dict] = None,
    fallback_mode: bool = False,
):
    """
    Создаёт клавиатуру с кнопками выбора качества.
    
    Args:
        sorted_qualities: Список доступных качеств (по убыванию)
        quality_sizes: Словарь размеров файлов для каждого качества
        fallback_mode: Если True, не показывает размеры файлов
    
    Returns:
        InlineKeyboardMarkup объект для aiogram
    """
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = []
    for q in sorted_qualities:
        if not fallback_mode and quality_sizes and q in quality_sizes:
            total_bytes = quality_sizes[q]
            if total_bytes > 0:
                size_mb = total_bytes / 1024 / 1024
                label = f"{q}p  |  {size_mb:.0f} МБ"
            else:
                label = f"{q}p"
        else:
            label = f"{q}p"
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"video_{q}")])
    keyboard.append([InlineKeyboardButton(text="🎵 Аудио (MP3)", callback_data="audio")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
