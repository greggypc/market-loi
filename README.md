# Market LOI Dashboard

Automated premarket data capture and Levels of Interest (LOI) report for your
personal watchlist. Runs entirely in the cloud — no need to wake up early or
keep your computer on.

---

## What It Does

| Time (CT) | Action |
|---|---|
| **3:00AM** | Captures bid/ask snapshot at the 4AM ET premarket open |
| **3:00AM** | Emails you the snapshot report immediately |
| **8:00AM** | Calculates full LOIs for all tickers (30 min before open) |
| **8:00AM** | Emails you the LOI report |
| **All day** | Web dashboard available at your Railway URL |

---

## The Two Morning Emails

### Email 1 — 3AM Snapshot
Subject line: `3AM Snapshot YYYY-MM-DD`

Shows the first bid/ask of the day for every ticker at premarket open:
- Bid / Ask / Spread / Midpoint
- Last price and Prior Close
- Spread is color-coded: green = tight, red = wide (> $0.10)
- Cash indices (SPX, NDX) flagged as derived — no premarket bid/ask

### Email 2 — 8AM LOI Report
Subject line: `LOI Report YYYY-MM-DD`

Full Levels of Interest for every ticker, organized by sector:
- Prior Day High / Low / Close
- Premarket High / Low / VWAP / Midpoint
- Gap % (premarket open vs prior day close) — green if up, red if down
- Round number support/resistance levels (nearest 50-cent increments)

---

## Web Dashboard

Available at your Railway URL any time of day. Three tabs:

**9AM LOIs** — Full LOI table organized by sector. Shows all premarket
levels, gap analysis, and round number levels.

**3AM Snapshot** — Bid/ask table from premarket open organized by sector.

**⚙ Manage Watchlist** — Add and remove tickers without touching any code:
- Type a symbol and click **Verify** — checks Tradier in real time and
  shows the company name, exchange, and last price before you commit
- Prevents duplicates automatically
- Click the red ✕ next to any ticker to remove it
- Changes take effect on the next scheduled run

---

## Your Watchlist (43 Tickers)

| Sector | Tickers |
|---|---|
| Indexes | SPY, QQQ, SPX*, NDX* |
| Semiconductors | NVDA, AMD, AVGO, MU, MRVL, INTC, QCOM, TXN, ARM, SNDK, CEVA, WOLF, COHR |
| Tech / Cloud / AI | MSFT, META, ORCL, IBM, NOW, PLTR, CRWD, APP, CSCO, VRT, PENG, NBIS, CRWV, TEM |
| Networking / Comms | APH, TE, IREN, ONDS, AAOI, TSSI, ATXI |
| Crypto Mining | MARA, RIOT, CLSK |
| Aerospace | FLY |
| Clean Energy | ENPH |

*SPX and NDX are cash indices — Tradier returns derived values, no premarket bid/ask.
SPY and QQQ are their tradeable ETF proxies with full premarket data.

---

## Column Reference

| Column | Meaning |
|---|---|
| PD High / Low / Close | Prior trading day OHLC |
| PM High / Low | Premarket high/low (3AM–8:29AM CT) |
| PM VWAP | Volume-weighted avg price of the premarket session |
| PM Mid | Midpoint of the premarket range — key LOI |
| Gap% | (PM open − PD close) / PD close |
| Round Levels | Nearby 50-cent support/resistance levels |
| Spread | Ask − Bid at 3AM; red if > $0.10 |
| derived | Cash index — no premarket bid/ask available |

---

## Tech Stack

| Component | Service | Cost |
|---|---|---|
| Script hosting & scheduling | Railway.app | Free ($5 credit/mo) |
| Database | Supabase (PostgreSQL) | Free |
| Market data | Tradier Brokerage API | Already paid |
| Email delivery | Gmail SMTP | Free |

---

## File Overview

| File | Purpose |
|---|---|
| `main.py` | Entry point — starts scheduler + Flask dashboard |
| `config.py` | API credentials, sector list, schedule times |
| `tradier.py` | All Tradier API calls (quotes, history, verify) |
| `db.py` | Supabase read/write + watchlist CRUD |
| `job_4am.py` | 3AM snapshot job |
| `job_9am.py` | 8AM LOI calculation job |
| `email_report.py` | Builds and sends both HTML emails |
| `dashboard.py` | Flask web dashboard with watchlist management |
| `schema.sql` | Original Supabase table definitions |
| `schema_watchlist.sql` | Watchlist table + seed data (run once) |
| `test_connection.py` | Local test before deploying |
| `requirements.txt` | Python dependencies |
| `Procfile` | Railway start command |

---

## Environment Variables (Railway)

Set these in Railway → your project → Variables:

| Variable | Value |
|---|---|
| `TRADIER_TOKEN` | Your Tradier production access token |
| `EMAIL_SENDER` | Gmail address you send FROM |
| `EMAIL_PASSWORD` | Gmail App Password (16 chars, not your login password) |
| `EMAIL_RECEIVER` | Address to receive reports (can be same as sender) |
| `SUPABASE_URL` | https://xxxxxxxxxxxx.supabase.co (no trailing slash) |
| `SUPABASE_KEY` | Your Supabase service_role key (starts with eyJ...) |

---

## Initial Setup (First Time Only)

### 1. Supabase — Create Tables

1. Go to supabase.com → your project → **SQL Editor** → **New Query**
2. Paste contents of `schema.sql` → **Run** (creates snapshots and LOI tables)
3. New query → paste contents of `schema_watchlist.sql` → **Run**
   (creates watchlist table and seeds all 43 tickers)
4. Go to **Settings → API** and copy your Project URL and service_role key

### 2. Gmail App Password

1. Go to myaccount.google.com → **Security** → **2-Step Verification**
2. Scroll to **App passwords** → create one named "Market LOI"
3. Copy the 16-character password — you only see it once

### 3. GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/market-loi.git
git push -u origin main
```

### 4. Railway

1. railway.app → **New Project** → **Deploy from GitHub repo**
2. Select your `market-loi` repo
3. Go to **Variables** tab → add all 6 environment variables
4. Go to **Settings → Networking** → **Generate Domain** → bookmark the URL

### 5. Test Locally (Optional)

```bash
pip3 install requests
export TRADIER_TOKEN=your_token_here
python3 test_connection.py
```

---

## Updating Your Watchlist

No code changes needed. Use the **⚙ Manage Watchlist** tab on your dashboard:

**Add a ticker:**
1. Type the symbol in the Symbol box
2. Choose a sector from the dropdown
3. Click **Verify →** to confirm Tradier has data for it
4. Click **✓ Confirm** to save

**Remove a ticker:**
1. Find it in the current watchlist table
2. Click the red ✕ button → confirm
3. It's removed immediately from future runs

---

## Updating Code

When you receive updated files, replace them locally and push:

```bash
git add .
git commit -m "Update description here"
git push
```

Railway detects the push and redeploys automatically within ~60 seconds.

---

## Troubleshooting

**Dashboard shows no data** — check Railway logs for errors. Most likely
a missing or incorrect environment variable. Verify `SUPABASE_URL` has
`https://` and no trailing slash.

**401 Unauthorized from Tradier** — your `TRADIER_TOKEN` is wrong or
missing. Make sure it's the Production token from tradier.com → Account
→ API Access, not the sandbox token.

**Email not arriving** — check spam folder first. Then verify `EMAIL_PASSWORD`
is the Gmail App Password (16 chars), not your regular Gmail password.
2-Step Verification must be enabled on the Gmail account.

**SPX/NDX show no bid/ask** — expected behavior. They are cash indices
with no directly tradeable bid/ask. Use SPY and QQQ as proxies.

**Railway free credit runs out** — a lightweight twice-daily script uses
roughly 50–100 compute hours per month, well within the $5 free credit.
If you add many more tickers or features, monitor usage in Railway's
Usage tab.

**Ticker verify fails for a valid symbol** — Tradier may not carry that
symbol, or it may be a futures/forex/crypto symbol. The tool only supports
US equities listed on NYSE and NASDAQ.
