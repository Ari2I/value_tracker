"""
Unit-тесты для модуля api_client (CbrRateProvider, fetch_rates).

Сетевые запросы не выполняются — requests.get подменяется моками,
чтобы тесты были быстрыми, детерминированными и не зависели от
доступности внешнего сервера.

Запуск:
    python -m unittest tests.test_api_client -v
"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from api_client import CbrRateProvider, CurrencyApiError, fetch_rates


def make_valid_payload():
    return {
        "Date": "2026-06-30T11:30:00+03:00",
        "Valute": {
            "USD": {
                "CharCode": "USD",
                "Name": "Доллар США",
                "Nominal": 1,
                "Value": 90.0,
                "Previous": 89.5,
            },
            "EUR": {
                "CharCode": "EUR",
                "Name": "Евро",
                "Nominal": 1,
                "Value": 98.0,
                "Previous": 99.0,
            },
        },
    }


class FetchRatesSuccessTest(unittest.TestCase):
    @patch("api_client.requests.get")
    def test_fetch_returns_parsed_rates(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = make_valid_payload()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_rates()

        self.assertEqual(result["date"], "2026-06-30T11:30:00+03:00")
        self.assertEqual(len(result["rates"]), 2)
        codes = {r.char_code for r in result["rates"]}
        self.assertEqual(codes, {"USD", "EUR"})

    @patch("api_client.requests.get")
    def test_fetch_skips_malformed_entries(self, mock_get):
        payload = make_valid_payload()
        # Добавляем запись с некорректным значением курса.
        payload["Valute"]["BAD"] = {
            "CharCode": "BAD",
            "Name": "Сломанная валюта",
            "Nominal": 1,
            "Value": "не число",
            "Previous": 1.0,
        }
        mock_response = MagicMock()
        mock_response.json.return_value = payload
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_rates()

        codes = {r.char_code for r in result["rates"]}
        self.assertNotIn("BAD", codes)
        self.assertEqual(len(result["rates"]), 2)


class FetchRatesErrorTest(unittest.TestCase):
    @patch("api_client.requests.get")
    def test_timeout_raises_currency_api_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()
        with self.assertRaises(CurrencyApiError):
            fetch_rates()

    @patch("api_client.requests.get")
    def test_connection_error_raises_currency_api_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaises(CurrencyApiError):
            fetch_rates()

    @patch("api_client.requests.get")
    def test_http_error_raises_currency_api_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError("500 Server Error")
        )
        mock_get.return_value = mock_response
        with self.assertRaises(CurrencyApiError):
            fetch_rates()

    @patch("api_client.requests.get")
    def test_invalid_json_raises_currency_api_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("not json")
        mock_get.return_value = mock_response
        with self.assertRaises(CurrencyApiError):
            fetch_rates()

    @patch("api_client.requests.get")
    def test_missing_valute_field_raises_currency_api_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"Date": "2026-06-30"}
        mock_get.return_value = mock_response
        with self.assertRaises(CurrencyApiError):
            fetch_rates()


class CbrRateProviderTest(unittest.TestCase):
    @patch("api_client.requests.get")
    def test_uses_custom_url_and_timeout(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = make_valid_payload()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = CbrRateProvider(api_url="https://example.com/rates", timeout=5)
        provider.fetch()

        mock_get.assert_called_once_with(
            "https://example.com/rates", timeout=5
        )


if __name__ == "__main__":
    unittest.main()
