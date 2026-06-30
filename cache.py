"""
Модуль кэширования курсов валют.

Хранит последний успешно полученный с сервера ответ локально, чтобы
приложение могло показать пользователю данные (с пометкой о том,
что они устарели), даже если на момент запуска нет соединения с
интернетом или сервер недоступен.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from api_client import CurrencyRate
from config import CACHE_FILE_PATH

logger = logging.getLogger(__name__)


def save_cache(rates: List[CurrencyRate], source_date: str) -> None:
    """
    Сохраняет текущие курсы в локальный файл кэша.

    Ошибки записи кэша не критичны для работы приложения, поэтому
    они только логируются, а не пробрасываются дальше.
    """
    payload = {
        "source_date": source_date,
        "rates": [r.to_dict() for r in rates],
    }
    try:
        path = Path(CACHE_FILE_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.warning("Не удалось сохранить кэш курсов: %s", exc)


def load_cache() -> Optional[Dict]:
    """
    Загружает курсы валют из локального кэша.

    Возвращает:
        Словарь {"date": str, "rates": List[CurrencyRate]} либо
        None, если кэш отсутствует или повреждён.
    """
    path = Path(CACHE_FILE_PATH)
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        rates = [
            CurrencyRate(
                char_code=item["char_code"],
                name=item["name"],
                nominal=item["nominal"],
                value=item["value"],
                previous=item["previous"],
            )
            for item in data["rates"]
        ]
        return {"date": data.get("source_date"), "rates": rates}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        logger.warning("Не удалось прочитать кэш курсов: %s", exc)
        return None
