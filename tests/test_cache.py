"""
Unit-тесты для модуля cache (save_cache / load_cache).

Запуск:
    python -m unittest tests.test_cache -v
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from api_client import CurrencyRate


def make_sample_rates():
    return [
        CurrencyRate("USD", "Доллар США", 1, 90.0, 89.5),
        CurrencyRate("EUR", "Евро", 1, 98.0, 99.0),
    ]


class CacheTest(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = os.path.join(tmp_dir, "cache.json")
            with patch("cache.CACHE_FILE_PATH", cache_path):
                import cache

                cache.save_cache(make_sample_rates(), "2026-06-30")
                loaded = cache.load_cache()

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["date"], "2026-06-30")
            self.assertEqual(len(loaded["rates"]), 2)
            self.assertEqual(loaded["rates"][0].char_code, "USD")

    def test_load_cache_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = os.path.join(tmp_dir, "does_not_exist.json")
            with patch("cache.CACHE_FILE_PATH", cache_path):
                import cache

                result = cache.load_cache()

            self.assertIsNone(result)

    def test_load_cache_returns_none_for_corrupted_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = os.path.join(tmp_dir, "broken.json")
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write("это не json {{{")
            with patch("cache.CACHE_FILE_PATH", cache_path):
                import cache

                result = cache.load_cache()

            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
