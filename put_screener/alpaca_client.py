"""Thin wrapper around Alpaca's trading + market-data REST APIs for options.

Alpaca splits options data across two APIs that we merge into one chain shape:
  - Trading API "options contracts" endpoint: strike, expiration, open interest.
    https://docs.alpaca.markets/reference/get-options-contracts
  - Market Data API "options snapshots" endpoint: quotes, greeks, IV.
    https://docs.alpaca.markets/reference/optionchain

The merged records are shaped to match what put_screener.screener expects
(the same shape TradierClient produces), so screener.py needs no changes.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import requests

_TIMEOUT = 15
_CONTRACTS_PAGE_LIMIT = 1000
_MAX_CONTRACT_PAGES = 10
# How far out to look when discovering expirations -- generous padding beyond
# any reasonable dte_max so weekly/monthly expirations aren't missed.
_EXPIRATION_DISCOVERY_WINDOW_DAYS = 100


class AlpacaClient:
    def __init__(
        self,
        key_id: str,
        secret_key: str,
        trading_base_url: str = "https://api.alpaca.markets",
        data_base_url: str = "https://data.alpaca.markets",
        feed: str = "indicative",
    ):
        self._trading_base_url = trading_base_url.rstrip("/")
        self._data_base_url = data_base_url.rstrip("/")
        self._feed = feed
        self._session = requests.Session()
        self._session.headers.update(
            {
                "APCA-API-KEY-ID": key_id,
                "APCA-API-SECRET-KEY": secret_key,
                "Accept": "application/json",
            }
        )

    def _get(self, base_url: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
        resp = self._session.get(f"{base_url}{path}", params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def get_quote(self, symbol: str) -> dict[str, Any] | None:
        data = self._get(
            self._data_base_url,
            f"/v2/stocks/{symbol}/trades/latest",
            {"feed": "iex"},
        )
        trade = data.get("trade")
        if not trade or trade.get("p") is None:
            return None
        return {"last": trade["p"]}

    def _get_contracts(
        self, symbol: str, expiration_gte: str, expiration_lte: str
    ) -> list[dict[str, Any]]:
        contracts: list[dict[str, Any]] = []
        page_token: str | None = None

        for _ in range(_MAX_CONTRACT_PAGES):
            params: dict[str, Any] = {
                "underlying_symbols": symbol,
                "type": "put",
                "status": "active",
                "expiration_date_gte": expiration_gte,
                "expiration_date_lte": expiration_lte,
                "limit": _CONTRACTS_PAGE_LIMIT,
            }
            if page_token:
                params["page_token"] = page_token

            data = self._get(self._trading_base_url, "/v2/options/contracts", params)
            contracts.extend(data.get("option_contracts") or [])

            page_token = data.get("next_page_token")
            if not page_token:
                break

        return contracts

    def get_expirations(self, symbol: str) -> list[str]:
        today = date.today()
        lte = today + timedelta(days=_EXPIRATION_DISCOVERY_WINDOW_DAYS)
        contracts = self._get_contracts(symbol, today.isoformat(), lte.isoformat())
        return sorted({c["expiration_date"] for c in contracts})

    def get_option_chain(self, symbol: str, expiration: str) -> list[dict[str, Any]]:
        contracts = self._get_contracts(symbol, expiration, expiration)
        if not contracts:
            return []

        contracts_by_symbol = {c["symbol"]: c for c in contracts}

        snapshots: dict[str, Any] = {}
        page_token: str | None = None
        for _ in range(_MAX_CONTRACT_PAGES):
            params: dict[str, Any] = {
                "feed": self._feed,
                "type": "put",
                "expiration_date": expiration,
                "limit": _CONTRACTS_PAGE_LIMIT,
            }
            if page_token:
                params["page_token"] = page_token

            data = self._get(
                self._data_base_url,
                f"/v1beta1/options/snapshots/{symbol}",
                params,
            )
            snapshots.update(data.get("snapshots") or {})

            page_token = data.get("next_page_token")
            if not page_token:
                break

        chain: list[dict[str, Any]] = []
        for contract_symbol, snapshot in snapshots.items():
            contract = contracts_by_symbol.get(contract_symbol)
            if contract is None:
                continue

            quote = snapshot.get("latestQuote") or {}
            greeks = snapshot.get("greeks") or {}
            iv = snapshot.get("impliedVolatility")
            daily_bar = snapshot.get("dailyBar") or {}

            open_interest_raw = contract.get("open_interest")
            open_interest = int(open_interest_raw) if open_interest_raw else 0

            chain.append(
                {
                    "option_type": "put",
                    "strike": float(contract["strike_price"]),
                    "bid": quote.get("bp"),
                    "ask": quote.get("ap"),
                    "open_interest": open_interest,
                    "volume": daily_bar.get("v"),
                    "greeks": {
                        "delta": greeks.get("delta"),
                        "mid_iv": iv,
                    },
                }
            )

        return chain
