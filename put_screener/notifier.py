"""Send the daily picks to Telegram as a monospace table.

Telegram has no real table element, but wrapping fixed-width columns in an
HTML <pre> block renders as an aligned table in any client.
"""
from __future__ import annotations

import html
from datetime import date, datetime

import requests

from .config import Config
from .screener import PutOpportunity

_TELEGRAM_MAX_LEN = 4096

_COLUMNS = (
    "SYM",
    "SPOT",
    "EXP",
    "STRK",
    "DTE",
    "BID",
    "DLT",
    "IV%",
    "ANN%",
    "OI",
    "SPRD%",
    "CAPITAL",
)
_ROW_FORMAT = "{:<5} {:>5} {:>5} {:>4} {:>3} {:>5} {:>4} {:>3} {:>5} {:>6} {:>5} {:>8}"


def _format_table(opportunities: list[PutOpportunity]) -> str:
    header = _ROW_FORMAT.format(*_COLUMNS)
    rows = [header, "-" * len(header)]

    for o in opportunities:
        exp_short = datetime.strptime(o.expiration, "%Y-%m-%d").strftime("%m/%d")
        spread_pct = (o.ask - o.bid) / o.mid * 100 if o.mid > 0 else 0.0
        rows.append(
            _ROW_FORMAT.format(
                o.symbol,
                f"{o.underlying_price:.0f}",
                exp_short,
                f"{o.strike:g}",
                o.dte,
                f"{o.bid:.2f}",
                f"{o.delta:.2f}",
                f"{o.iv * 100:.0f}",
                f"{o.annualized_return_pct:.1f}",
                f"{o.open_interest:,}",
                f"{spread_pct:.1f}",
                f"{o.capital_required:,.0f}",
            )
        )

    return "\n".join(rows)


def format_message(opportunities: list[PutOpportunity]) -> str:
    header_line = f"<b>Put Screener - {date.today().isoformat()}</b>"

    if not opportunities:
        return f"{header_line}\n\nNo candidates matched today's criteria."

    table = html.escape(_format_table(opportunities))
    return f"{header_line}\n<pre>{table}</pre>"


def send_telegram_message(message: str, cfg: Config) -> None:
    if len(message) > _TELEGRAM_MAX_LEN:
        raise ValueError(
            f"Message is {len(message)} chars, over Telegram's {_TELEGRAM_MAX_LEN} "
            "limit -- reduce scoring.max_results in config.yaml."
        )

    url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage"
    resp = requests.post(
        url,
        json={
            "chat_id": cfg.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML",
        },
        timeout=15,
    )
    resp.raise_for_status()


def send_telegram_photo(photo_bytes: bytes, caption: str, cfg: Config) -> None:
    url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendPhoto"
    resp = requests.post(
        url,
        data={"chat_id": cfg.telegram_chat_id, "caption": caption},
        files={"photo": ("picks.png", photo_bytes, "image/png")},
        timeout=30,
    )
    resp.raise_for_status()
