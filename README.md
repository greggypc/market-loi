# Market LOI Dashboard

Automated premarket data capture and Levels of Interest report for 44 tickers.

- **3:00AM CT** — captures bid/ask snapshot at premarket open (= 4AM ET)
- **8:00AM CT** — calculates LOIs, sends email report, updates dashboard (30 min before open)

---

## What You'll Need Before Starting

- Tradier brokerage account with API token
- Gmail account (to send reports from)
- GitHub account (free)
- Supabase account (free) — supabase.com
- Railway account (free) — railway.app

---

## Step 1 — Get Your Tradier API Token

1. Log in to tradier.com
2. Go to **Account → API Access** (or Settings → API)
3. Copy your **Production Access Token** (not the sandbox one)
4. Keep it handy — you'll add it to Railway later

---

## Step 2 — Set Up Gmail App Password

Gmail requires an "App Password" for SMTP access (not your regular password).

1. Go to myaccount.google.com
2. Click **Security** → **2-Step Verification** (must be enabled)
3. Scroll down to **App passwords**
4. Select app: **Mail** → device: **Other** → type "Market LOI"
5. Copy the 16-character password — you only see it once

---

## Step 3 — Set Up Supabase

1. Go to supabase.com → **New Project**
2. Name it `market-loi`, choose a region close to you (US East)
3. Wait ~2 minutes for it to provision
4. Go to **SQL Editor** → **New Query**
5. Paste the entire contents of `schema.sql` → click **Run**
6. You should see "Success" for both tables
7. Go to **Settings → API** and copy:
   - **Project URL** (looks like `https://xxxx.supabase.co`)
   - **service_role** key (under "Project API keys" — use service_role, not anon)

---

## Step 4 — Push to GitHub

```bash
# In your terminal, from this folder:
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/market-loi.git
git push -u origin main
```

(Create the `market-loi` repo on github.com first — empty, no README)

---

## Step 5 — Deploy to Railway

1. Go to railway.app → **New Project** → **Deploy from GitHub repo**
2. Select your `market-loi` repo
3. Railway will detect Python and start building automatically

### Add Environment Variables

In Railway → your project → **Variables** tab, add these one by one:

| Variable | Value |
|---|---|
| `TRADIER_TOKEN` | Your Tradier production token |
| `EMAIL_SENDER` | youraddress@gmail.com |
| `EMAIL_PASSWORD` | The 16-char Gmail App Password |
| `EMAIL_RECEIVER` | Address to receive reports (can be same) |
| `SUPABASE_URL` | https://xxxx.supabase.co |
| `SUPABASE_KEY` | Your Supabase service_role key |

4. Railway will redeploy automatically after you add variables
5. Go to **Settings → Networking** → **Generate Domain**
   - You'll get a URL like `market-loi-production.up.railway.app`
   - This is your dashboard URL — bookmark it

---

## Step 6 — Test the Connection (Optional but Recommended)

Before waiting until 4AM, you can test locally:

```bash
pip install requests
export TRADIER_TOKEN=your_token_here
python test_connection.py
```

You should see quotes, prior day OHLC, and a premarket note.

---

## Step 7 — Verify It's Running

1. Open your Railway dashboard URL in a browser
2. You should see the LOI Dashboard (empty until first run)
3. Check **Railway → Deployments → Logs** to watch the scheduler start up
4. First email arrives the next morning after 9AM CT

---

## Dashboard URL

Your dashboard will be live at:
`https://market-loi-production.up.railway.app`

Two tabs:
- **9AM LOIs** — prior day OHLC, premarket range, VWAP, gap%, round levels
- **4AM Snapshot** — bid, ask, spread, midpoint at premarket open

---

## File Overview

| File | Purpose |
|---|---|
| `main.py` | Entry point — runs scheduler + Flask dashboard |
| `config.py` | Watchlist, sectors, settings |
| `tradier.py` | All Tradier API calls |
| `db.py` | Supabase read/write |
| `job_4am.py` | 4AM snapshot job |
| `job_9am.py` | 9AM LOI calculation job |
| `email_report.py` | Builds and sends HTML email |
| `dashboard.py` | Flask web dashboard |
| `schema.sql` | Supabase table definitions |
| `test_connection.py` | Local test before deploying |
| `requirements.txt` | Python dependencies |

---

## Columns Reference

| Column | Meaning |
|---|---|
| PD High/Low/Close | Prior trading day OHLC |
| PM High/Low | Premarket high/low (4AM–9:29AM CT) |
| PM VWAP | Volume-weighted avg price of premarket session |
| PM Mid | Midpoint of premarket range — key LOI |
| Gap% | (PM open − PD close) / PD close |
| Round Levels | Nearby 50-cent support/resistance levels |
| derived | Cash index (SPX/NDX) — no premarket bid/ask |

---

## Troubleshooting

**Email not arriving** — check Gmail App Password is correct, not your regular password

**No data in dashboard** — check Railway logs for errors; verify TRADIER_TOKEN is the production token not sandbox

**SPX/NDX show no bid/ask** — this is expected; they're cash indices with derived values only

**Railway free tier credit runs out** — the $5/month credit covers ~700 hours; a lightweight process like this uses roughly 50–100 hours/month, well within the limit
