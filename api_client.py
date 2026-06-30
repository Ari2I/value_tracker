"""
Модуль для получения актуальных курсов валют.

Используется публичный бесплатный API Центрального Банка РФ
(зеркало https://www.cbr-xml-daily.ru/daily_json.js), не требующий
регистрации, API-ключа или авторизации.

Доступ к данным реализован через интерфейс RateProvider, что
позволяет в будущем подключить альтернативный источник курсов
(другой API, локальный файл и т.д.), не меняя остальной код
приложения — достаточно реализовать новый класс-провайдер с
методом fetch().
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import requests

from config import CBR_API_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


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


class RateProvider(ABC):
    """
    Абстрактный интерфейс источника курсов валют.

    Любой класс, реализующий метод fetch(), может быть использован
    приложением как источник данных — это упрощает добавление новых
    API или тестового (mock) провайдера без изменения GUI/CLI кода.
    """

    @abstractmethod
    def fetch(self) -> Dict:
        """
        Возвращает словарь {"date": str, "rates": List[CurrencyRate]}.

        Исключения:
            CurrencyApiError: при любой ошибке получения данных.
        """
        raise NotImplementedError


class CbrRateProvider(RateProvider):
    """Провайдер курсов валют на основе API ЦБ РФ (зеркало cbr-xml-daily)."""

    def __init__(
        self, api_url: str = CBR_API_URL, timeout: int = REQUEST_TIMEOUT
    ) -> None:
        self.api_url = api_url
        self.timeout = timeout

    def fetch(self) -> Dict:
        try:
            response = requests.get(self.api_url, timeout=self.timeout)
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


def fetch_rates(provider: RateProvider | None = None) -> Dict:
    """
    Получает текущие курсы валют через указанный провайдер.

    Аргументы:
        provider: источник данных. По умолчанию используется
            CbrRateProvider (API ЦБ РФ).

    Возвращает:
        Словарь с датой обновления и списком объектов CurrencyRate.

    Исключения:
        CurrencyApiError: при сетевой ошибке, таймауте или
            некорректном ответе сервера.
    """
    provider = provider or CbrRateProvider()
    return provider.fetch()
