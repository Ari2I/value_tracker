"""
Модуль для получения актуальных курсов валют.

Используется публичный бесплатный API Центрального Банка РФ
(зеркало https://www.cbr-xml-daily.ru/daily_json.js), не требующий
регистрации, API-ключа или авторизации.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)

CBR_API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
REQUEST_TIMEOUT = 10  # секунд


class CurrencyApiError(Exception):
    """Исключение, возникающее при ошибках получения данных о курсах."""


@dataclass
class CurrencyRate:
    """Структура данных одной валюты."""

    char_code: str
    name: str
    nominal: int
    value: float
    previous: float

    @property
    def change(self) -> float:
        """Изменение курса относительно предыдущего значения."""
        return round(self.value - self.previous, 4)

    @property
    def change_percent(self) -> float:
        """Изменение курса в процентах."""
        if self.previous == 0:
            return 0.0
        return round((self.change / self.previous) * 100, 4)

    def to_dict(self) -> Dict:
        """Преобразование в словарь для сериализации в JSON."""
        return {
            "char_code": self.char_code,
            "name": self.name,
            "nominal": self.nominal,
            "value": self.value,
            "previous": self.previous,
            "change": self.change,
            "change_percent": self.change_percent,
        }


def fetch_rates() -> Dict:
    """
    Получает текущие курсы валют с внешнего API.

    Возвращает словарь с датой обновления и списком объектов CurrencyRate.

    Исключения:
        CurrencyApiError: при сетевой ошибке, таймауте или некорректном
        ответе сервера.
    """
    try:
        response = requests.get(CBR_API_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout as exc:
        logger.error("Превышено время ожидания ответа от сервера")
        raise CurrencyApiError("Сервер не отвечает (таймаут)") from exc
    except requests.exceptions.ConnectionError as exc:
        logger.error("Ошибка соединения с сервером")
        raise CurrencyApiError(
            "Нет соединения с сервером. Проверьте интернет"
        ) from exc
    except requests.exceptions.HTTPError as exc:
        logger.error("HTTP ошибка: %s", exc)
        raise CurrencyApiError(f"Ошибка сервера: {exc}") from exc
    except ValueError as exc:
        logger.error("Не удалось разобрать ответ сервера как JSON")
        raise CurrencyApiError("Некорректный ответ сервера") from exc

    try:
        valute = data["Valute"]
        date_str = data.get("Date", datetime.now().isoformat())
    except KeyError as exc:
        raise CurrencyApiError(
            "Структура ответа сервера изменилась, не найдено поле Valute"
        ) from exc

    rates: List[CurrencyRate] = []
    for item in valute.values():
        try:
            rates.append(
                CurrencyRate(
                    char_code=item["CharCode"],
                    name=item["Name"],
                    nominal=int(item["Nominal"]),
                    value=float(item["Value"]),
                    previous=float(item["Previous"]),
                )
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Пропущена некорректная запись валюты: %s", exc)
            continue

    logger.info("Получено %d курсов валют", len(rates))
    return {"date": date_str, "rates": rates}