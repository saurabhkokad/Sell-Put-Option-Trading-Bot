"""Build the ticker universe: S&P 500 + Nasdaq 100 constituents."""
from __future__ import annotations

import logging

import pandas as pd

log = logging.getLogger(__name__)

SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_WIKI_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"
# Wikipedia's Nasdaq-100 page no longer embeds the constituent table, so this
# maintained listing page is the primary source; Wikipedia is kept as a
# best-effort fallback in case that ever changes back.
NASDAQ100_STOCKANALYSIS_URL = "https://stockanalysis.com/list/nasdaq-100-stocks/"

_HEADERS = {"User-Agent": "Mozilla/5.0 (put-screener)"}


def _normalize(symbol: str) -> str:
    # Keep dots as-is (e.g. "BRK.B") -- this is the format Alpaca's stock and
    # options APIs expect. reference_data.py converts to dash-form for yfinance.
    return symbol.strip().upper()


def _find_ticker_column(table: pd.DataFrame) -> str | None:
    for col in table.columns:
        if str(col).strip().lower() in ("ticker", "symbol"):
            return col
    return None


def get_sp500_tickers() -> list[str]:
    tables = pd.read_html(SP500_WIKI_URL, storage_options=_HEADERS)
    df = tables[0]
    return [_normalize(s) for s in df["Symbol"].tolist()]


def get_nasdaq100_tickers() -> list[str]:
    try:
        tables = pd.read_html(NASDAQ100_STOCKANALYSIS_URL, storage_options=_HEADERS)
        for table in tables:
            col = _find_ticker_column(table)
            if col is not None and len(table) >= 90:
                return [_normalize(s) for s in table[col].tolist()]
    except Exception as exc:
        log.warning("stockanalysis.com Nasdaq-100 fetch failed: %s", exc)

    try:
        tables = pd.read_html(NASDAQ100_WIKI_URL, storage_options=_HEADERS)
        for table in tables:
            col = _find_ticker_column(table)
            if col is not None and len(table) >= 90:
                return [_normalize(s) for s in table[col].tolist()]
    except Exception as exc:
        log.warning("Wikipedia Nasdaq-100 fetch failed: %s", exc)

    raise RuntimeError(
        "Could not fetch the Nasdaq-100 constituent list from any known source. "
        "Check NASDAQ100_STOCKANALYSIS_URL / NASDAQ100_WIKI_URL in universe.py "
        "for a site restructure."
    )


def get_universe() -> list[str]:
    sp500 = get_sp500_tickers()
    nasdaq100 = get_nasdaq100_tickers()
    return sorted(set(sp500) | set(nasdaq100))
