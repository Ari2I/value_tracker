"""
Графический интерфейс приложения "Курсы валют".

Использует стандартную библиотеку tkinter, поэтому не требует
установки дополнительных GUI-зависимостей.

Особенности интерфейса:
    * курсы валют загружаются автоматически сразу при запуске
      приложения, без необходимости нажимать кнопку;
    * любое изменение фильтров (текст, диапазон курса, поле и
      направление сортировки) применяется мгновенно, без отдельной
      кнопки «Применить»;
    * все надписи и подсказки в интерфейсе фильтров — на русском
      языке;
    * текстовый фильтр по коду/названию валюты регистронезависим —
      можно вводить в любом регистре ("usd", "USD", "Доллар").
"""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from api_client import CurrencyApiError, CurrencyRate, fetch_rates
from filters import SORT_KEY_LABELS, filter_rates, sort_rates
from storage import save_rates_to_json

logger = logging.getLogger(__name__)

COLUMNS = ("code", "name", "nominal", "value", "change", "change_percent")
COLUMN_TITLES = {
    "code": "Код",
    "name": "Название",
    "nominal": "Номинал",
    "value": "Курс",
    "change": "Изменение",
    "change_percent": "Изменение, %",
}

# Список вариантов сортировки на русском языке (то, что видит
# пользователь в выпадающем списке).
SORT_LABELS = list(SORT_KEY_LABELS.values())
# Обратное сопоставление "русская подпись" -> "внутренний ключ".
LABEL_TO_SORT_KEY = {label: key for key, label in SORT_KEY_LABELS.items()}


class CurrencyApp(tk.Tk):
    """Главное окно приложения."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Курсы валют")
        self.geometry("820x520")
        self.minsize(700, 450)

        self.all_rates: List[CurrencyRate] = []
        self.displayed_rates: List[CurrencyRate] = []
        self.source_date: Optional[str] = None

        # Флаг нужен, чтобы не запускать фильтрацию во время
        # программной инициализации переменных интерфейса.
        self._ui_ready = False

        self._build_widgets()
        self._ui_ready = True

        # Автоматическая загрузка курсов сразу при запуске приложения.
        self.after(100, self.update_rates)

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        self.update_button = ttk.Button(
            top_frame, text="Обновить курсы", command=self.update_rates
        )
        self.update_button.pack(side=tk.LEFT, padx=(0, 10))

        self.status_label = ttk.Label(top_frame, text="Загрузка курсов...")
        self.status_label.pack(side=tk.LEFT)

        filter_frame = ttk.LabelFrame(self, text="Фильтры", padding=10)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(filter_frame, text="Код или название валюты:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 5)
        )
        self.code_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.code_var, width=18).grid(
            row=0, column=1, padx=(0, 15)
        )

        ttk.Label(filter_frame, text="Курс от:").grid(row=0, column=2, sticky=tk.W)
        self.min_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.min_var, width=10).grid(
            row=0, column=3, padx=(5, 15)
        )

        ttk.Label(filter_frame, text="Курс до:").grid(row=0, column=4, sticky=tk.W)
        self.max_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.max_var, width=10).grid(
            row=0, column=5, padx=(5, 15)
        )

        ttk.Label(filter_frame, text="Сортировать по:").grid(
            row=0, column=6, sticky=tk.W
        )
        self.sort_var = tk.StringVar(value=SORT_KEY_LABELS["code"])
        sort_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.sort_var,
            values=SORT_LABELS,
            state="readonly",
            width=16,
        )
        sort_combo.grid(row=0, column=7, padx=(5, 15))

        self.desc_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            filter_frame, text="По убыванию", variable=self.desc_var
        ).grid(row=0, column=8, padx=(0, 15))

        # Мгновенное применение фильтров при любом изменении значений:
        # текстовые поля — через trace на StringVar, выпадающий список
        # сортировки и переключатель направления — через trace на их
        # переменные. Отдельная кнопка "Применить" не нужна.
        self.code_var.trace_add("write", self._on_filters_changed)
        self.min_var.trace_add("write", self._on_filters_changed)
        self.max_var.trace_add("write", self._on_filters_changed)
        self.sort_var.trace_add("write", self._on_filters_changed)
        self.desc_var.trace_add("write", self._on_filters_changed)

        # Таблица результатов
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(
            table_frame, columns=COLUMNS, show="headings"
        )
        for col in COLUMNS:
            self.tree.heading(col, text=COLUMN_TITLES[col])
            self.tree.column(col, width=110, anchor=tk.CENTER)
        self.tree.column("name", width=220, anchor=tk.W)

        scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        bottom_frame = ttk.Frame(self, padding=10)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.save_button = ttk.Button(
            bottom_frame,
            text="Сохранить в JSON",
            command=self.save_to_json,
            state=tk.DISABLED,
        )
        self.save_button.pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # Логика приложения
    # ------------------------------------------------------------------
    def update_rates(self) -> None:
        """Запускает обновление курсов в отдельном потоке."""
        self.update_button.config(state=tk.DISABLED)
        self.status_label.config(text="Загрузка...")
        thread = threading.Thread(target=self._fetch_in_background, daemon=True)
        thread.start()

    def _fetch_in_background(self) -> None:
        try:
            result = fetch_rates()
            self.all_rates = result["rates"]
            self.source_date = result["date"]
            self.after(0, self._on_fetch_success)
        except CurrencyApiError as exc:
            message = str(exc)
            self.after(0, lambda: self._on_fetch_error(message))

    def _on_fetch_success(self) -> None:
        self.status_label.config(
            text=(
                f"Загружено {len(self.all_rates)} валют. "
                f"Дата: {self.source_date}"
            )
        )
        self.update_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.NORMAL)
        self.apply_filters()

    def _on_fetch_error(self, message: str) -> None:
        self.status_label.config(text="Ошибка загрузки данных")
        self.update_button.config(state=tk.NORMAL)
        messagebox.showerror("Ошибка", message)

    def _on_filters_changed(self, *_args) -> None:
        """Обработчик изменения любого из фильтров (вызывается trace)."""
        if not self._ui_ready:
            return
        self.apply_filters()

    def apply_filters(self) -> None:
        """Применяет фильтры и сортировку к загруженным данным."""
        if not self.all_rates:
            # Данные ещё не загружены (например, идёт автозагрузка
            # при старте) — просто очищаем таблицу, без всплывающих
            # окон, чтобы не мешать запуску приложения.
            self._refresh_table()
            return

        min_value = self._parse_float(self.min_var.get())
        max_value = self._parse_float(self.max_var.get())

        filtered = filter_rates(
            self.all_rates,
            code_substring=self.code_var.get() or None,
            min_value=min_value,
            max_value=max_value,
        )

        sort_key = LABEL_TO_SORT_KEY.get(self.sort_var.get(), "code")
        try:
            sorted_rates = sort_rates(
                filtered,
                sort_by=sort_key,
                descending=self.desc_var.get(),
            )
        except ValueError as exc:
            messagebox.showerror("Ошибка фильтра", str(exc))
            return

        self.displayed_rates = sorted_rates
        self._refresh_table()

    def _refresh_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for rate in self.displayed_rates:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    rate.char_code,
                    rate.name,
                    rate.nominal,
                    f"{rate.value:.4f}",
                    f"{rate.change:+.4f}",
                    f"{rate.change_percent:+.2f}",
                ),
            )

    def save_to_json(self) -> None:
        """Сохраняет текущий отфильтрованный список в JSON-файл."""
        if not self.displayed_rates:
            messagebox.showinfo(
                "Нет данных",
                "Нет данных для сохранения. Измените фильтры "
                "или обновите курсы",
            )
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")],
            initialfile="currency_rates.json",
            title="Сохранить курсы валют",
        )
        if not file_path:
            return

        try:
            save_rates_to_json(
                self.displayed_rates, file_path, source_date=self.source_date
            )
        except OSError as exc:
            messagebox.showerror(
                "Ошибка сохранения", f"Не удалось сохранить файл: {exc}"
            )
            return

        count = len(self.displayed_rates)
        messagebox.showinfo(
            "Готово", f"Сохранено {count} записей в файл:\n{file_path}"
        )

    @staticmethod
    def _parse_float(text: str) -> Optional[float]:
        text = text.strip().replace(",", ".")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None


def run_app() -> None:
    """Точка запуска графического интерфейса."""
    app = CurrencyApp()
    app.mainloop()