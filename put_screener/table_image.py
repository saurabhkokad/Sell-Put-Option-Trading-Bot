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

_COLUMNS = [
    "Sym",
    "Spot",
    "Exp",
    "Strike",
    "DTE",
    "Bid",
    "Delta",
    "IV / HV (ratio)",
    "Ann%",
    "OI",
    "Spread",
]
_HEADER_COLOR = "#2c3e50"
_HEADER_TEXT_COLOR = "white"
_ROW_COLORS = ["#ffffff", "#f2f2f2"]
_FONT_SIZE = 15
_DPI = 100

# All measurements in inches. The table gets an explicit bbox sized to fit
# exactly this many rows, with title/bottom margins reserved outside of it --
# this guarantees no overlap regardless of row count (a table placed with
# loc="center" instead can auto-center and overflow past its axes' top edge).
_ROW_HEIGHT_IN = 0.48
_TITLE_MARGIN_IN = 0.8
_BOTTOM_MARGIN_IN = 0.35


def _format_spread(o: PutOpportunity) -> str:
    spread_dollars = o.ask - o.bid
    spread_pct = spread_dollars / o.mid * 100 if o.mid > 0 else 0.0
    return f"${spread_dollars:.2f} / {spread_pct:.1f}%"


def _format_iv_hv(o: PutOpportunity) -> str:
    iv_pct = o.iv * 100
    if o.hv is None or o.hv <= 0:
        return f"{iv_pct:.0f}% / n/a"
    hv_pct = o.hv * 100
    ratio = o.iv / o.hv
    return f"{iv_pct:.0f}% / {hv_pct:.0f}% ({ratio:.1f}x)"


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
        _format_iv_hv(o),
        f"{o.annualized_return_pct:.1f}%",
        f"{o.open_interest:,}",
        _format_spread(o),
    ]


def render_table_image(opportunities: list[PutOpportunity]) -> bytes:
    rows = [_row_values(o) for o in opportunities]
    n_display_rows = len(rows) + 1  # +1 for the header row

    fig_width = 0.95 * len(_COLUMNS)
    table_height_in = n_display_rows * _ROW_HEIGHT_IN
    fig_height = _TITLE_MARGIN_IN + table_height_in + _BOTTOM_MARGIN_IN

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    axes_bottom = _BOTTOM_MARGIN_IN / fig_height
    axes_top = 1 - (_TITLE_MARGIN_IN / fig_height)
    fig.subplots_adjust(left=0.02, right=0.98, bottom=axes_bottom, top=axes_top)
    ax.axis("off")

    ax.set_title(
        f"Put Screener - {date.today().isoformat()}",
        fontsize=18,
        fontweight="bold",
        pad=14,
    )

    table = ax.table(
        cellText=rows,
        colLabels=_COLUMNS,
        cellLoc="center",
        bbox=[0, 0, 1, 1],  # fill the axes region exactly -- no auto-overflow
    )
    table.auto_set_font_size(False)
    table.set_fontsize(_FONT_SIZE)
    table.auto_set_column_width(col=list(range(len(_COLUMNS))))

    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor("#dddddd")
        if row == 0:
            cell.set_facecolor(_HEADER_COLOR)
            cell.set_text_props(color=_HEADER_TEXT_COLOR, fontweight="bold")
        else:
            cell.set_facecolor(_ROW_COLORS[row % 2])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
