"""
Unit-тесты для модуля cli (режим командной строки без GUI).

Запуск:
    python -m unittest tests.test_cli -v
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from api_client import CurrencyApiError, CurrencyRate
from cli import build_parser, run_cli


def make_sample_rates():
    return [
        CurrencyRate("USD", "Доллар США", 1, 90.0, 89.5),
        CurrencyRate("EUR", "Евро", 1, 98.0, 99.0),
    ]


class RunCliTest(unittest.TestCase):
    def _parse(self, extra_args):
        parser = build_parser()
        return parser.parse_args(["--no-gui"] + extra_args)

    @patch("cli.save_cache")
    @patch("cli.fetch_rates")
    def test_successful_fetch_saves_file(self, mock_fetch, mock_save_cache):
        mock_fetch.return_value = {
            "date": "2026-06-30",
            "rates": make_sample_rates(),
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "out.json")
            args = self._parse(["--output", output_path])

            exit_code = run_cli(args)

            self.assertEqual(exit_code, 0)
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["count"], 2)

    @patch("cli.save_cache")
    @patch("cli.fetch_rates")
    def test_filter_by_code_applied(self, mock_fetch, mock_save_cache):
        mock_fetch.return_value = {
            "date": "2026-06-30",
            "rates": make_sample_rates(),
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "out.json")
            args = self._parse(["--output", output_path, "--code", "usd"])

            run_cli(args)

            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["rates"][0]["char_code"], "USD")

    @patch("cli.load_cache")
    @patch("cli.fetch_rates")
    def test_fetch_error_falls_back_to_cache(self, mock_fetch, mock_load_cache):
        mock_fetch.side_effect = CurrencyApiError("сервер недоступен")
        mock_load_cache.return_value = {
            "date": "2026-06-29",
            "rates": make_sample_rates(),
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "out.json")
            args = self._parse(["--output", output_path])

            exit_code = run_cli(args)

            self.assertEqual(exit_code, 0)
            self.assertTrue(os.path.exists(output_path))

    @patch("cli.load_cache")
    @patch("cli.fetch_rates")
    def test_fetch_error_without_cache_returns_error_code(
        self, mock_fetch, mock_load_cache
    ):
        mock_fetch.side_effect = CurrencyApiError("сервер недоступен")
        mock_load_cache.return_value = None
        args = self._parse(["--output", "unused.json"])

        exit_code = run_cli(args)

        self.assertEqual(exit_code, 1)

    @patch("cli.save_cache")
    @patch("cli.fetch_rates")
    def test_invalid_sort_key_rejected_by_argparse(self, mock_fetch, mock_save_cache):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["--no-gui", "--sort", "unknown"])


if __name__ == "__main__":
    unittest.main()
