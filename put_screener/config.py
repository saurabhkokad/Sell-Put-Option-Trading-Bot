"""Load and expose the screener's tunable configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


@dataclass(frozen=True)
class Config:
    min_market_cap: float
    avoid_earnings_before_expiration: bool

    dte_min: int
    dte_max: int

    abs_delta_min: float
    abs_delta_max: float
    min_iv: float
    min_open_interest: int
    min_volume: int
    max_bid_ask_spread_pct: float
    min_bid: float

    min_annualized_return_pct: float
    max_results: int

    alpaca_key_id: str
    alpaca_secret_key: str
    alpaca_trading_base_url: str
    telegram_bot_token: str
    telegram_chat_id: str


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> Config:
    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    alpaca_key_id = os.environ.get("ALPACA_API_KEY_ID", "")
    alpaca_secret_key = os.environ.get("ALPACA_API_SECRET_KEY", "")
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not alpaca_key_id or not alpaca_secret_key:
        raise RuntimeError(
            "ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY environment variables must be set."
        )
    if not telegram_bot_token or not telegram_chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables must be set."
        )

    return Config(
        min_market_cap=float(raw["universe"]["min_market_cap"]),
        avoid_earnings_before_expiration=bool(
            raw["universe"]["avoid_earnings_before_expiration"]
        ),
        dte_min=int(raw["expiration"]["dte_min"]),
        dte_max=int(raw["expiration"]["dte_max"]),
        abs_delta_min=float(raw["option_filters"]["abs_delta_min"]),
        abs_delta_max=float(raw["option_filters"]["abs_delta_max"]),
        min_iv=float(raw["option_filters"]["min_iv"]),
        min_open_interest=int(raw["option_filters"]["min_open_interest"]),
        min_volume=int(raw["option_filters"]["min_volume"]),
        max_bid_ask_spread_pct=float(raw["option_filters"]["max_bid_ask_spread_pct"]),
        min_bid=float(raw["option_filters"]["min_bid"]),
        min_annualized_return_pct=float(raw["scoring"]["min_annualized_return_pct"]),
        max_results=int(raw["scoring"]["max_results"]),
        alpaca_key_id=alpaca_key_id,
        alpaca_secret_key=alpaca_secret_key,
        alpaca_trading_base_url=os.environ.get(
            "ALPACA_TRADING_BASE_URL", "https://api.alpaca.markets"
        ),
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
    )
