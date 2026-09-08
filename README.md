# Sell Put Option Trading Bot

A daily screener that scans S&P 500 + Nasdaq 100 tickers for cash-secured put
opportunities (high IV, low delta, 30-45 DTE) and pushes the top picks to your
phone via Telegram every weekday morning. It only screens and notifies — it
never places trades.

## How it works

1. Builds a ticker universe from S&P 500 + Nasdaq 100 constituents.
2. For each ticker, pulls option chains + greeks from **Alpaca**, filters to
   puts with delta/IV/DTE/liquidity matching `config.yaml`, and skips names
   with earnings before expiration (gap risk).
3. Computes annualized return on capital for every candidate.
4. Picks the single best strike per ticker, ranks across tickers, keeps the
   top N (`scoring.max_results` in config).
5. Renders the picks as a table image (via matplotlib) and sends it to your
   phone via a **Telegram bot**. If image rendering or sending fails for any
   reason, it automatically falls back to a plain-text monospace table so
   you still get notified.
6. Runs automatically every weekday morning via **GitHub Actions** — no
   laptop required to be on.

## One-time setup

### 1. Alpaca account (options data with real greeks)

1. Sign up at https://alpaca.markets and get your brokerage account approved.
2. In the Alpaca dashboard, generate an **API key pair** — you'll get a
   `Key ID` and a `Secret Key`. These are your `ALPACA_API_KEY_ID` and
   `ALPACA_API_SECRET_KEY`.
3. Alpaca's free tier gives "indicative" (slightly delayed) real-time options
   data including greeks and IV, computed via Black-Scholes — fine for a
   once-a-day screen. Real-time OPRA data requires their paid Algo Trader
   Plus plan ($99/mo); not needed for this use case.
4. Keep `ALPACA_TRADING_BASE_URL` as `https://api.alpaca.markets` for a live
   account (use `https://paper-api.alpaca.markets` if you're testing against
   a paper account instead).

### 2. Telegram bot (push notifications)

1. In Telegram, message **[@BotFather](https://t.me/BotFather)** and send
   `/newbot`. Follow the prompts; you'll get a bot token — that's your
   `TELEGRAM_BOT_TOKEN`.
2. Send any message to your new bot (search for it by the username you gave
   it) so it has a conversation to reply into.
3. Get your chat ID: open
   `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in a browser
   after step 2, and look for `"chat":{"id": ...}` in the JSON. That number
   is your `TELEGRAM_CHAT_ID`.

### 3. Push this project to GitHub

```bash
cd "Sell Put Option Trading Bot"
git init
git add .
git commit -m "Initial put screener"
git branch -M main
git remote add origin <your-new-empty-github-repo-url>
git push -u origin main
```

### 4. Add secrets to the GitHub repo

In your repo: **Settings → Secrets and variables → Actions → New repository
secret**. Add each of:

- `ALPACA_API_KEY_ID`
- `ALPACA_API_SECRET_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

That's it. The workflow in `.github/workflows/screen.yml` runs every weekday
at 13:45 UTC (~9:45am ET) and will message you the picks. You can also
trigger it manually anytime from the **Actions** tab → "Daily Put Screener"
→ **Run workflow**.

## Running locally (for testing before you push)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your real tokens
python main.py
```

### Keeping secrets out of the repo entirely

`.env` is already gitignored, but for extra safety you can keep your real
credentials in a file outside the project altogether (so they'd never be at
risk even if `.gitignore` were ever misconfigured), and have `.env` just
point at it:

```bash
mkdir -p ~/.secrets && chmod 700 ~/.secrets
# create ~/.secrets/sell-put-bot.env with your real ALPACA_*/TELEGRAM_* values
chmod 600 ~/.secrets/sell-put-bot.env
```

Then `.env` in the project only needs one line:

```
ENV_FILE=~/.secrets/sell-put-bot.env
```

`main.py` loads `.env` first, and if `ENV_FILE` is set, loads that file's
values on top of it. This only affects local runs — GitHub Actions never
touches `.env` at all; it reads credentials from repo Secrets directly.

## Tuning the screen

All thresholds live in `config.yaml`:

| Setting | Meaning |
|---|---|
| `min_market_cap` | Minimum market cap filter (S&P 500 + Nasdaq 100 already implies large/mega-cap) |
| `dte_min` / `dte_max` | Days-to-expiration window (default 30-45) |
| `abs_delta_min` / `abs_delta_max` | Put delta range — lower = further OTM = safer/lower premium |
| `min_iv` | Minimum implied volatility floor |
| `min_open_interest`, `min_volume`, `max_bid_ask_spread_pct`, `min_bid` | Liquidity filters so you're not trading illiquid, wide-spread contracts |
| `min_annualized_return_pct` | Minimum annualized yield to bother showing you |
| `max_results` | How many picks show up in the notification |

Each pick's notification includes `capital_required` (strike × 100) — position
sizing across your $100K is left to you rather than enforced by the screener,
since a single contract on a mega-cap name can already run $20K-$60K+.

## Important caveats — please read

- **This is a screener, not an auto-trader.** It never places orders. You
  review the picks and decide whether/how to act.
- **Your stated goal (30-40% annual return on $100K via cash-secured puts)
  is aggressive.** Premium-selling income of that scale generally requires
  either concentrating in higher-volatility (higher-risk) names or deploying
  most of your capital with little cash buffer — both increase the odds of a
  large assignment or drawdown in a sharp selloff. Treat the annualized
  return numbers as gross, before-tax, before-assignment-risk figures, not a
  guaranteed yield.
- **IV filter is absolute, not IV Rank.** True IV Rank/Percentile needs a
  paid historical-IV data feed. `min_iv` here is a flat implied-volatility
  floor, not "IV relative to this stock's own 52-week range." A name can
  pass the filter with elevated IV that's actually normal for it (e.g.
  volatile growth stocks always run hot IV).
- **Earnings-date filtering is best-effort.** It relies on free Yahoo
  Finance data (`yfinance`), which can be missing or stale for some tickers.
  Always double check earnings dates yourself before selling a put through
  an earnings date.
- **Assignment risk is real.** Every pick here means you're willing to buy
  100 shares per contract at the strike if assigned. Make sure
  `capital_required` × contracts you'd actually sell stays within cash you
  are genuinely willing to hold that stock with.
