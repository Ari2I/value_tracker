"""
Точка входа в приложение "Курсы валют".

Запуск:
    python main.py
"""

from __future__ import annotations

import logging

from gui import run_app


def configure_logging() -> None:
    """Настраивает базовое логирование приложения."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> None:
    configure_logging()
    run_app()


if __name__ == "__main__":
    main()