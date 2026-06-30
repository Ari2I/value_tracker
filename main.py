"""
Точка входа в приложение "Курсы валют".

Запуск с графическим интерфейсом (по умолчанию):
    python main.py

Запуск в режиме командной строки (без GUI):
    python main.py --no-gui
    python main.py --no-gui --output rates.json --code USD
"""

from __future__ import annotations

import logging
import sys

from cli import build_parser, run_cli


def configure_logging() -> None:
    """Настраивает базовое логирование приложения."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> None:
    configure_logging()

    parser = build_parser()
    args = parser.parse_args()

    if args.no_gui:
        sys.exit(run_cli(args))

    # Импорт gui откладывается до этого момента, чтобы CLI-режим
    # можно было использовать в окружениях без tkinter (например,
    # в Docker-контейнере без графической подсистемы).
    from gui import run_app

    run_app()


if __name__ == "__main__":
    main()
