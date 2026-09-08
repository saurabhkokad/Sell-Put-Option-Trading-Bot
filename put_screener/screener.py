"""Core screening logic: find cash-secured put candidates matching our criteria."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date

from .alpaca_client import AlpacaClient
from .config import Config
from .reference_data import get_market_cap, get_next_earnings_date
from .util import dte

log = logging.getLogger(__name__)

MAX_WORKERS = 8


@dataclass
class PutOpportunity:
    symbol: str
    underlying_price: float
    expiration: str
    dte: int
    strike: float
    bid: float
    ask: float
    mid: float
    delta: float
    iv: float
    open_interest: int
    volume: int
    annualized_return_pct: float
    return_on_capital_pct: float
    capital_required: float


def _bid_ask_spread_pct(bid: float, ask: float) -> float | None:
    mid = (bid + ask) / 2
    if mid <= 0:
        return None
    return (ask - bid) / mid


def _screen_symbol(
    client: AlpacaClient, symbol: str, cfg: Config
) -> list[PutOpportunity]:
    opportunities: list[PutOpportunity] = []

    market_cap = get_market_cap(symbol)
    if market_cap is not None and market_cap < cfg.min_market_cap:
        return opportunities

    quote = client.get_quote(symbol)
    if not quote or quote.get("last") is None:
        return opportunities
    underlying_price = float(quote["last"])

    earnings_date: date | None = None
    if cfg.avoid_earnings_before_expiration:
        earnings_date = get_next_earnings_date(symbol)

    try:
        expirations = client.get_expirations(symbol)
    except Exception as exc:
        log.warning("expirations lookup failed for %s: %s", symbol, exc)
        return opportunities

    candidate_expirations = []
    for exp in expirations:
        days = dte(exp)
        if cfg.dte_min <= days <= cfg.dte_max:
            candidate_expirations.append((exp, days))

    for expiration, days in candidate_expirations:
        if earnings_date is not None:
            exp_date = date.fromisoformat(expiration)
            if earnings_date <= exp_date:
                continue  # earnings fall before/at expiration -- skip, gap risk

        try:
            chain = client.get_option_chain(symbol, expiration)
        except Exception as exc:
            log.warning("chain lookup failed for %s %s: %s", symbol, expiration, exc)
            continue

        for opt in chain:
            if opt.get("option_type") != "put":
                continue
            greeks = opt.get("greeks") or {}
            delta = greeks.get("delta")
            iv = greeks.get("mid_iv") or greeks.get("smv_vol")
            if delta is None or iv is None:
                continue

            abs_delta = abs(float(delta))
            if not (cfg.abs_delta_min <= abs_delta <= cfg.abs_delta_max):
                continue
            if float(iv) < cfg.min_iv:
                continue

            bid = float(opt.get("bid") or 0)
            ask = float(opt.get("ask") or 0)
            if bid < cfg.min_bid:
                continue

            spread_pct = _bid_ask_spread_pct(bid, ask)
            if spread_pct is None or spread_pct > cfg.max_bid_ask_spread_pct:
                continue

            open_interest = int(opt.get("open_interest") or 0)
            if open_interest < cfg.min_open_interest:
                continue
            volume = int(opt.get("volume") or 0)
            if volume < cfg.min_volume:
                continue

            strike = float(opt["strike"])
            capital_required = strike * 100
            premium = bid * 100  # conservative: what you'd actually receive
            return_on_capital_pct = (premium / capital_required) * 100
            annualized_return_pct = return_on_capital_pct * (365 / days)

            if annualized_return_pct < cfg.min_annualized_return_pct:
                continue

            opportunities.append(
                PutOpportunity(
                    symbol=symbol,
                    underlying_price=underlying_price,
                    expiration=expiration,
                    dte=days,
                    strike=strike,
                    bid=bid,
                    ask=ask,
                    mid=(bid + ask) / 2,
                    delta=float(delta),
                    iv=float(iv),
                    open_interest=open_interest,
                    volume=volume,
                    annualized_return_pct=annualized_return_pct,
                    return_on_capital_pct=return_on_capital_pct,
                    capital_required=capital_required,
                )
            )

    return opportunities


def run_screen(universe: list[str], cfg: Config) -> list[PutOpportunity]:
    client = AlpacaClient(
        cfg.alpaca_key_id, cfg.alpaca_secret_key, cfg.alpaca_trading_base_url
    )
    all_opportunities: list[PutOpportunity] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_screen_symbol, client, symbol, cfg): symbol
            for symbol in universe
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                all_opportunities.extend(future.result())
            except Exception as exc:
                log.warning("screening failed for %s: %s", symbol, exc)

    return all_opportunities
