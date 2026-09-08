"""Write the day's picks to JSON so other tools (e.g. a Claude Code routine
reading this repo) can pick up the results without needing live API access."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from .screener import PutOpportunity

PICKS_DIR = Path("picks")


def _opportunity_to_dict(o: PutOpportunity) -> dict:
    d = asdict(o)
    d["iv_hv_ratio"] = round(o.iv / o.hv, 3) if o.hv and o.hv > 0 else None
    return d


def write_picks_json(
    picks: list[PutOpportunity], universe_size: int, raw_candidate_count: int
) -> Path:
    PICKS_DIR.mkdir(exist_ok=True)
    today = date.today().isoformat()

    payload = {
        "date": today,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "universe_size": universe_size,
        "raw_candidate_count": raw_candidate_count,
        "picks": [_opportunity_to_dict(o) for o in picks],
    }
    content = json.dumps(payload, indent=2)

    dated_path = PICKS_DIR / f"{today}.json"
    dated_path.write_text(content)
    (PICKS_DIR / "latest.json").write_text(content)
    return dated_path
