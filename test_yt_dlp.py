#!/usr/bin/env python3
"""
Утилита для проверки работоспособности yt-dlp.
Используется для отладки ошибок загрузки.
"""

import yt_dlp
import sys

def check_yt_dlp(url: str):
    """Проверяет может ли yt-dlp загрузить информацию о видео."""
    
    print(f"🔍 Проверяю: {url}\n")
    
    ydl_opts = {
        'quiet': False,
        'no_warnings': False,
        'retries': 5,
        'socket_timeout': 30,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("📥 Получаю информацию о видео...\n")
            info = ydl.extract_info(url, download=False)
            
            print("✅ УСПЕШНО!\n")
            print(f"📝 Название: {info.get('title', 'N/A')}")
            print(f"⏱️  Длительность: {info.get('duration', 'N/A')} сек")
            print(f"👤 Автор: {info.get('uploader', 'N/A')}")
            print(f"📊 Качества доступны: {len(info.get('formats', []))}")
            
            # Выводим доступные качества
            if 'formats' in info and len(info['formats']) > 0:
                print("\n📐 Доступные качества:")
                for fmt in info['formats'][:10]:  # Показываем первые 10
                    if fmt.get('height'):
                        print(f"  - {fmt.get('height')}p: {fmt.get('ext', 'N/A')}")
            
            return True
            
    except Exception as e:
        print(f"❌ ОШИБКА: {type(e).__name__}")
        print(f"📌 {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Введите URL видео: ").strip()
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    success = check_yt_dlp(url)
    sys.exit(0 if success else 1)
