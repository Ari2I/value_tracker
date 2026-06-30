"""
Модуль сохранения курсов валют в JSON-файл.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from api_client import CurrencyRate

logger = logging.getLogger(__name__)


def save_rates_to_json(
    rates: Iterable[CurrencyRate],
    file_path: str,
    source_date: Optional[str] = None,
) -> None:
    """
    Сохраняет список курсов валют в JSON-файл.

    Аргументы:
        rates: список объектов CurrencyRate для сохранения.
        file_path: путь к итоговому JSON-файлу.
        source_date: дата актуальности курсов (из ответа API).

    Исключения:
        OSError: при ошибке записи файла на диск.
    """
    rates_list = list(rates)
    payload = {
        "source_date": source_date,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(rates_list),
        "rates": [r.to_dict() for r in rates_list],
    }

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.error("Не удалось записать файл %s: %s", file_path, exc)
        raise

    logger.info("Сохранено %d записей в файл %s", payload["count"], file_path)
