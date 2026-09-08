"""Best-effort fundamental/reference data (market cap, next earnings date) via yfinance.

These calls are treated as advisory, not authoritative: since our universe is already
S&P 500 + Nasdaq 100 (all large/mega-cap by index membership), a failed lookup here
should never abort the screen for that ticker -- we just skip the earnings-blackout
check for it and fall back to trusting index membership for the market-cap filter.
"""
from __future__ import annotations

import logging
import threading
from datetime import date, datetime

import numpy as np
import yfinance as yf

_HV_WINDOW_DAYS = 20
_TRADING_DAYS_PER_YEAR = 252

log = logging.getLogger(__name__)

# yfinance shares a local sqlite cache (cookies/session) across instances, which
# raises "database is locked" under concurrent access from our thread pool.
# Serializing all yfinance calls behind one lock avoids that at negligible cost.
_YFINANCE_LOCK = threading.Lock()


def _to_yfinance_symbol(symbol: str) -> str:
    # Alpaca/OCC use dot-form share classes (e.g. "BRK.B"); yfinance uses dash-form.
    return symbol.replace(".", "-")


def get_market_cap(symbol: str) -> float | None:
    symbol = _to_yfinance_symbol(symbol)
    try:
        with _YFINANCE_LOCK:
            info = yf.Ticker(symbol).fast_info
            cap = info.get("market_cap") or info.get("marketCap")
        return float(cap) if cap else None
    except Exception as exc:  # yfinance can raise a variety of network/parse errors
        log.warning("market cap lookup failed for %s: %s", symbol, exc)
        return None


def get_historical_volatility(symbol: str, window: int = _HV_WINDOW_DAYS) -> float | None:
    """Trailing realized volatility, annualized, as a decimal (e.g. 0.42 for 42%)."""
    symbol = _to_yfinance_symbol(symbol)
    try:
        with _YFINANCE_LOCK:
            hist = yf.Ticker(symbol).history(period=f"{window + 10}d")
        closes = hist["Close"].dropna()
        if len(closes) < window + 1:
            return None
        log_returns = np.log(closes / closes.shift(1)).dropna()
        daily_std = log_returns.tail(window).std()
        return float(daily_std * np.sqrt(_TRADING_DAYS_PER_YEAR))
    except Exception as exc:
        log.warning("historical volatility lookup failed for %s: %s", symbol, exc)
        return None


def get_next_earnings_date(symbol: str) -> date | None:
    symbol = _to_yfinance_symbol(symbol)
    try:
        with _YFINANCE_LOCK:
            df = yf.Ticker(symbol).get_earnings_dates(limit=4)
        if df is None or df.empty:
            return None
        today = datetime.now(df.index.tz) if df.index.tz else datetime.now()
        future = df[df.index >= today]
        if future.empty:
            return None
        return future.index.min().date()
    except Exception as exc:
        log.warning("earnings date lookup failed for %s: %s", symbol, exc)
        return None
