"""
Базовые unit-тесты для модулей filters и storage.

Запуск:
    python -m unittest tests.tests -v
"""

import json
import os
import tempfile
import unittest

from api_client import CurrencyRate
from filters import SORT_KEY_LABELS, filter_rates, sort_rates
from storage import save_rates_to_json


def make_sample_rates():
    return [
        CurrencyRate("USD", "Доллар США", 1, 90.0, 89.5),
        CurrencyRate("EUR", "Евро", 1, 98.0, 99.0),
        CurrencyRate("CNY", "Китайский юань", 10, 12.5, 12.4),
    ]


class FilterRatesTest(unittest.TestCase):
    def test_filter_by_code_lowercase(self):
        rates = make_sample_rates()
        result = filter_rates(rates, code_substring="usd")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].char_code, "USD")

    def test_filter_by_code_uppercase(self):
        rates = make_sample_rates()
        result = filter_rates(rates, code_substring="USD")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].char_code, "USD")

    def test_filter_by_code_mixed_case(self):
        rates = make_sample_rates()
        result = filter_rates(rates, code_substring="UsD")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].char_code, "USD")

    def test_filter_by_name_any_case(self):
        rates = make_sample_rates()
        result = filter_rates(rates, code_substring="ЕВРО")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].char_code, "EUR")

    def test_filter_by_min_max(self):
        rates = make_sample_rates()
        result = filter_rates(rates, min_value=50, max_value=95)
        codes = {r.char_code for r in result}
        self.assertEqual(codes, {"USD"})

    def test_filter_no_match(self):
        rates = make_sample_rates()
        result = filter_rates(rates, code_substring="xyz")
        self.assertEqual(result, [])

    def test_filter_empty_string_returns_all(self):
        rates = make_sample_rates()
        result = filter_rates(rates, code_substring="   ")
        self.assertEqual(len(result), 3)


class SortRatesTest(unittest.TestCase):
    def test_sort_by_value_ascending(self):
        rates = make_sample_rates()
        result = sort_rates(rates, sort_by="value", descending=False)
        values = [r.value for r in result]
        self.assertEqual(values, sorted(values))

    def test_sort_by_value_descending(self):
        rates = make_sample_rates()
        result = sort_rates(rates, sort_by="value", descending=True)
        values = [r.value for r in result]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_sort_invalid_key_raises(self):
        rates = make_sample_rates()
        with self.assertRaises(ValueError):
            sort_rates(rates, sort_by="unknown_key")

    def test_sort_key_labels_match_sort_keys(self):
        from filters import SORT_KEYS

        self.assertEqual(set(SORT_KEY_LABELS.keys()), set(SORT_KEYS.keys()))


class CurrencyRateCalculationsTest(unittest.TestCase):
    def test_change_positive(self):
        rate = CurrencyRate("USD", "Доллар США", 1, 90.0, 89.0)
        self.assertAlmostEqual(rate.change, 1.0)

    def test_change_percent(self):
        rate = CurrencyRate("USD", "Доллар США", 1, 110.0, 100.0)
        self.assertAlmostEqual(rate.change_percent, 10.0)

    def test_change_percent_zero_previous(self):
        rate = CurrencyRate("USD", "Доллар США", 1, 10.0, 0.0)
        self.assertEqual(rate.change_percent, 0.0)


class SaveRatesToJsonTest(unittest.TestCase):
    def test_save_and_read_back(self):
        rates = make_sample_rates()
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "rates.json")
            save_rates_to_json(rates, file_path, source_date="2026-06-30")

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data["count"], 3)
            self.assertEqual(data["source_date"], "2026-06-30")
            self.assertEqual(len(data["rates"]), 3)
            self.assertIn("change_percent", data["rates"][0])


if __name__ == "__main__":
    unittest.main()