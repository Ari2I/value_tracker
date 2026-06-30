"""
Конфигурация приложения "Курсы валют".

Все параметры можно переопределить через переменные окружения,
например при запуске:

    CURRENCY_API_URL=https://example.com/rates.json python main.py

Если установлен пакет python-dotenv и в корне проекта есть файл
.env, переменные будут подхвачены автоматически.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv — опциональная зависимость, без неё конфигурация
    # по-прежнему читает переменные окружения системы напрямую.
    pass


def _get_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


# URL источника данных о курсах валют.
CBR_API_URL: str = os.environ.get(
    "CURRENCY_API_URL", "https://www.cbr-xml-daily.ru/daily_json.js"
)

# Таймаут сетевого запроса в секундах.
REQUEST_TIMEOUT: int = _get_int("CURRENCY_REQUEST_TIMEOUT", 10)

# Путь к файлу, в который сохраняется последний успешно полученный
# ответ сервера — используется как резервный источник данных, если
# при следующем запуске сеть недоступна.
CACHE_FILE_PATH: str = os.environ.get(
    "CURRENCY_CACHE_FILE", str(Path.home() / ".currency_tracker_cache.json")
)

# Путь к файлу сохранения по умолчанию (используется в CLI-режиме,
# если пользователь не указал свой путь через --output).
DEFAULT_OUTPUT_PATH: str = os.environ.get(
    "CURRENCY_DEFAULT_OUTPUT", "currency_rates.json"
)
