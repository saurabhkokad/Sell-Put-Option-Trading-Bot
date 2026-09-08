"""Send the daily picks to Telegram."""
from __future__ import annotations

from datetime import date

import requests

from .config import Config
from .screener import PutOpportunity

_TELEGRAM_MAX_LEN = 4096


def format_message(opportunities: list[PutOpportunity]) -> str:
    lines = [f"Put Screener - {date.today().isoformat()}"]

    if not opportunities:
        lines.append("")
        lines.append("No candidates matched today's criteria.")
        return "\n".join(lines)

    for i, o in enumerate(opportunities, start=1):
        lines.append("")
        lines.append(f"{i}. {o.symbol}  (spot ${o.underlying_price:,.2f})")
        lines.append(f"   Sell {o.expiration} ${o.strike:g}P  ({o.dte}d)")
        lines.append(f"   Bid ${o.bid:.2f} | Delta {o.delta:.2f} | IV {o.iv * 100:.0f}%")
        lines.append(
            f"   Ann. Return {o.annualized_return_pct:.1f}% | OI {o.open_interest}"
        )
        lines.append(f"   Capital required: ${o.capital_required:,.0f}")

    return "\n".join(lines)


def send_telegram_message(message: str, cfg: Config) -> None:
    url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage"

    chunks = [
        message[i : i + _TELEGRAM_MAX_LEN]
        for i in range(0, len(message), _TELEGRAM_MAX_LEN)
    ] or [message]

    for chunk in chunks:
        resp = requests.post(
            url,
            json={"chat_id": cfg.telegram_chat_id, "text": chunk},
            timeout=15,
        )
        resp.raise_for_status()
