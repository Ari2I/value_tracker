"""
Режим командной строки приложения "Курсы валют".

Позволяет получить курсы, отфильтровать и отсортировать их, а затем
сохранить в JSON-файл без запуска графического интерфейса. Удобно
для использования в скриптах, cron-задачах или CI.

Примеры:
    python main.py --no-gui
    python main.py --no-gui --output rates.json
    python main.py --no-gui --code USD --output usd.json
    python main.py --no-gui --min 10 --max 100 --sort value --desc
"""

from __future__ import annotations

import argparse
import logging
import sys

from api_client import CurrencyApiError, fetch_rates
from cache import load_cache, save_cache
from config import DEFAULT_OUTPUT_PATH
from filters import SORT_KEYS, filter_rates, sort_rates
from storage import save_rates_to_json

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description=(
            "Получение, фильтрация, сортировка и сохранение курсов "
            "валют без графического интерфейса."
        )
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="запустить приложение в режиме командной строки",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help=(
            "путь к итоговому JSON-файлу "
            f"(по умолчанию: {DEFAULT_OUTPUT_PATH})"
        ),
    )
    parser.add_argument(
        "--code",
        default=None,
        help="фильтр по коду или названию валюты (например, USD)",
    )
    parser.add_argument(
        "--min", dest="min_value", type=float, default=None,
        help="минимальное значение курса",
    )
    parser.add_argument(
        "--max", dest="max_value", type=float, default=None,
        help="максимальное значение курса",
    )
    parser.add_argument(
        "--sort",
        choices=sorted(SORT_KEYS),
        default="code",
        help="поле сортировки (по умолчанию: code)",
    )
    parser.add_argument(
        "--desc",
        action="store_true",
        help="сортировать по убыванию (по умолчанию — по возрастанию)",
    )
    return parser


def run_cli(args: argparse.Namespace) -> int:
    """
    Выполняет получение, фильтрацию и сохранение курсов валют.

    Возвращает код завершения (0 — успех, 1 — ошибка).
    """
    try:
        result = fetch_rates()
        rates = result["rates"]
        source_date = result["date"]
        save_cache(rates, source_date or "")
        print(f"Получено {len(rates)} курсов валют. Дата: {source_date}")
    except CurrencyApiError as exc:
        logger.warning("Не удалось получить курсы с сервера: %s", exc)
        cached = load_cache()
        if not cached or not cached["rates"]:
            print(f"Ошибка: {exc}", file=sys.stderr)
            return 1
        rates = cached["rates"]
        source_date = cached["date"]
        print(
            f"Сервер недоступен ({exc}). Используются устаревшие данные "
            f"из кэша от {source_date}."
        )

    filtered = filter_rates(
        rates,
        code_substring=args.code,
        min_value=args.min_value,
        max_value=args.max_value,
    )

    try:
        sorted_rates = sort_rates(
            filtered, sort_by=args.sort, descending=args.desc
        )
    except ValueError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    if not sorted_rates:
        print("После применения фильтров не осталось ни одной валюты.")
        return 0

    try:
        save_rates_to_json(sorted_rates, args.output, source_date=source_date)
    except OSError as exc:
        print(f"Не удалось сохранить файл: {exc}", file=sys.stderr)
        return 1

    print(f"Сохранено {len(sorted_rates)} записей в файл: {args.output}")
    return 0
