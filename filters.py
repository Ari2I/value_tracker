"""
Модуль фильтрации и сортировки курсов валют.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from api_client import CurrencyRate


def filter_rates(
    rates: Iterable[CurrencyRate],
    code_substring: Optional[str] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> List[CurrencyRate]:
    """
    Фильтрует список курсов валют по заданным критериям.

    Поиск по коду/названию валюты регистронезависим: пользователь
    может вводить значение в любом регистре (например, "usd", "USD"
    или "UsD" — результат будет одинаковым).

    Аргументы:
        rates: исходный список курсов.
        code_substring: подстрока для поиска по буквенному коду
            или названию валюты (регистр не учитывается).
        min_value: минимальное значение курса (включительно).
        max_value: максимальное значение курса (включительно).

    Возвращает:
        Новый отфильтрованный список CurrencyRate.
    """
    result = list(rates)

    if code_substring:
        needle = code_substring.strip().lower()
        if needle:
            result = [
                r
                for r in result
                if needle in r.char_code.lower() or needle in r.name.lower()
            ]

    if min_value is not None:
        result = [r for r in result if r.value >= min_value]

    if max_value is not None:
        result = [r for r in result if r.value <= max_value]

    return result


SORT_KEYS = {
    "code": lambda r: r.char_code,
    "name": lambda r: r.name,
    "value": lambda r: r.value,
    "change": lambda r: r.change,
    "change_percent": lambda r: r.change_percent,
}

# Сопоставление внутренних ключей сортировки с их отображением
# на русском языке для интерфейса.
SORT_KEY_LABELS = {
    "code": "Код валюты",
    "name": "Название",
    "value": "Курс к рублю",
    "change": "Изменение",
    "change_percent": "Изменение, %",
}


def sort_rates(
    rates: Iterable[CurrencyRate],
    sort_by: str = "code",
    descending: bool = False,
) -> List[CurrencyRate]:
    """
    Сортирует список курсов валют по выбранному ключу.

    Аргументы:
        rates: список курсов для сортировки.
        sort_by: ключ сортировки, один из SORT_KEYS
            ("code", "name", "value", "change", "change_percent").
        descending: сортировать по убыванию, если True.

    Исключения:
        ValueError: если передан неизвестный ключ сортировки.
    """
    if sort_by not in SORT_KEYS:
        raise ValueError(
            f"Неизвестный ключ сортировки: {sort_by}. "
            f"Допустимые значения: {', '.join(SORT_KEYS)}"
        )
    key_func = SORT_KEYS[sort_by]
    return sorted(rates, key=key_func, reverse=descending)