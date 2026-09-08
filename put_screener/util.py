"""Small helpers shared across data-provider clients."""
from __future__ import annotations

from datetime import date, datetime


def dte(expiration: str, today: date | None = None) -> int:
    exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
    today = today or date.today()
    return (exp_date - today).days
