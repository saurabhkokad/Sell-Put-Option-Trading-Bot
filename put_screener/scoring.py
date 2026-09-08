"""Rank screened opportunities and select the final picks list."""
from __future__ import annotations

from .config import Config
from .screener import PutOpportunity


def rank_and_select(
    opportunities: list[PutOpportunity], cfg: Config
) -> list[PutOpportunity]:
    """Keep the single best expiration/strike per ticker, then rank across tickers.

    Capping at one pick per underlying keeps the final notification diversified
    rather than dominated by every strike on the single highest-IV name.
    """
    best_per_symbol: dict[str, PutOpportunity] = {}
    for opp in opportunities:
        current_best = best_per_symbol.get(opp.symbol)
        if current_best is None or opp.annualized_return_pct > current_best.annualized_return_pct:
            best_per_symbol[opp.symbol] = opp

    ranked = sorted(
        best_per_symbol.values(),
        key=lambda o: o.annualized_return_pct,
        reverse=True,
    )
    return ranked[: cfg.max_results]
