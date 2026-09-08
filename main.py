"""Entry point: build the universe, screen for put-selling candidates, notify Telegram."""
from __future__ import annotations

import logging
import os
import sys

from datetime import date

from put_screener.config import load_config
from put_screener.notifier import (
    format_message,
    send_telegram_message,
    send_telegram_photo,
)
from put_screener.scoring import rank_and_select
from put_screener.screener import run_screen
from put_screener.table_image import render_table_image
from put_screener.universe import get_universe

try:
    from dotenv import load_dotenv

    load_dotenv()  # local .env -- may just point at a real secrets file via ENV_FILE
    secrets_file = os.environ.get("ENV_FILE")
    if secrets_file:
        load_dotenv(os.path.expanduser(secrets_file), override=True)
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("main")


def main() -> int:
    cfg = load_config()

    log.info("Building ticker universe (S&P 500 + Nasdaq 100)...")
    universe = get_universe()
    log.info("Universe size: %d tickers", len(universe))

    log.info("Screening for cash-secured put candidates...")
    opportunities = run_screen(universe, cfg)
    log.info("Found %d raw candidates before ranking", len(opportunities))

    picks = rank_and_select(opportunities, cfg)
    log.info("Selected %d final picks", len(picks))

    message = format_message(picks)
    print(message)

    if picks:
        try:
            image_bytes = render_table_image(picks)
            caption = f"Put Screener - {date.today().isoformat()}"
            send_telegram_photo(image_bytes, caption, cfg)
            log.info("Notification sent (image).")
            return 0
        except Exception as exc:
            log.warning("Image notification failed, falling back to text: %s", exc)

    send_telegram_message(message, cfg)
    log.info("Notification sent (text).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
