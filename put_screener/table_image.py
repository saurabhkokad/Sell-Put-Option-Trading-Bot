"""Render the daily picks as a styled table image for Telegram's sendPhoto.

Using matplotlib rather than an HTML+headless-browser screenshot keeps this
dependency-light and reliable in CI: no browser binary to install or manage,
just a plotting library that already ships headless-safe (Agg backend).
"""
from __future__ import annotations

import io
from datetime import date, datetime

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .screener import PutOpportunity

_COLUMNS = ["Sym", "Spot", "Exp", "Strike", "DTE", "Bid", "Delta", "IV%", "Ann%"]
_HEADER_COLOR = "#2c3e50"
_HEADER_TEXT_COLOR = "white"
_ROW_COLORS = ["#ffffff", "#f2f2f2"]
_ROW_HEIGHT = 0.6
_FONT_SIZE = 11


def _row_values(o: PutOpportunity) -> list[str]:
    exp_short = datetime.strptime(o.expiration, "%Y-%m-%d").strftime("%m/%d")
    return [
        o.symbol,
        f"${o.underlying_price:,.2f}",
        exp_short,
        f"${o.strike:g}",
        str(o.dte),
        f"${o.bid:.2f}",
        f"{o.delta:.2f}",
        f"{o.iv * 100:.0f}%",
        f"{o.annualized_return_pct:.1f}%",
    ]


def render_table_image(opportunities: list[PutOpportunity]) -> bytes:
    rows = [_row_values(o) for o in opportunities]
    n_rows = len(rows)

    fig_height = 1.0 + n_rows * (_ROW_HEIGHT * 0.3)
    fig, ax = plt.subplots(figsize=(9, fig_height))
    ax.axis("off")

    ax.set_title(
        f"Put Screener - {date.today().isoformat()}",
        fontsize=14,
        fontweight="bold",
        pad=14,
    )

    table = ax.table(
        cellText=rows,
        colLabels=_COLUMNS,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(_FONT_SIZE)
    table.scale(1, _ROW_HEIGHT * 3)
    table.auto_set_column_width(col=list(range(len(_COLUMNS))))

    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor("#dddddd")
        if row == 0:
            cell.set_facecolor(_HEADER_COLOR)
            cell.set_text_props(color=_HEADER_TEXT_COLOR, fontweight="bold")
        else:
            cell.set_facecolor(_ROW_COLORS[row % 2])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
