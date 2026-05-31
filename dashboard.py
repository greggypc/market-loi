"""
Web Dashboard
─────────────
Flask app serving:
  - Today's 4AM snapshot and 8AM LOI data (two tabs)
  - Watchlist management: add ticker (with Tradier verification) and delete
"""

import logging
import os
from datetime import datetime
from functools import wraps
from zoneinfo import ZoneInfo
from flask import (Flask, render_template_string, jsonify,
                   request, session, redirect, url_for)

from db import fetch_latest, get_watchlist, add_ticker, remove_ticker, ticker_exists_in_watchlist
from tradier import verify_ticker
from config import SECTORS

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
app.secret_key = os.environ.get("DASHBOARD_SECRET", "change-me-in-railway")
CT  = ZoneInfo("America/Chicago")

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")


def login_required(f):
    """Decorator — redirects to login page if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not DASHBOARD_PASSWORD:
            return f(*args, **kwargs)          # no password set → open access
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def api_auth_required(f):
    """Decorator for API routes — returns 401 JSON if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not DASHBOARD_PASSWORD:
            return f(*args, **kwargs)
        if not session.get("authenticated"):
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ── Helpers ────────────────────────────────────────────────────────────────────

def fmt_val(val, decimals=2):
    if val is None:
        return "—"
    try:
        return f"{float(val):.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def fmt_pct(val):
    if val is None:
        return "—"
    try:
        v    = float(val)
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:.2f}%"
    except (TypeError, ValueError):
        return "—"


def group_by_sector(rows: list) -> dict:
    """Group rows preserving Supabase sector order."""
    grouped = {}
    for row in rows:
        s = row.get("sector", "Other")
        grouped.setdefault(s, []).append(row)
    return grouped


# ── HTML template ──────────────────────────────────────────────────────────────

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Market LOI Dashboard — {{ date }}</title>
  <style>
    :root {
      --bg:      #0f172a; --surface: #1e293b; --border: #334155;
      --text:    #e2e8f0; --muted:   #94a3b8; --accent: #38bdf8;
      --green:   #4ade80; --red:     #f87171; --head-bg:#1e3a5f;
      --orange:  #fb923c;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background:var(--bg); color:var(--text);
           font-family:'Courier New',monospace; font-size:12px; padding:16px; }
    header { display:flex; align-items:baseline; gap:16px;
             border-bottom:1px solid var(--border); padding-bottom:10px; margin-bottom:16px; }
    header h1 { font-size:18px; color:var(--accent); }
    header span { color:var(--muted); font-size:11px; }
    .tabs { display:flex; gap:8px; margin-bottom:12px; }
    .tab { padding:5px 14px; border-radius:4px; cursor:pointer;
           background:var(--surface); color:var(--muted);
           border:1px solid var(--border); font-size:11px; font-family:inherit; }
    .tab.active { background:var(--head-bg); color:var(--accent); border-color:var(--accent); }
    .panel { display:none; }
    .panel.active { display:block; }
    .sector-label { background:var(--surface); color:var(--accent); font-weight:700;
                    padding:5px 10px; font-size:11px; letter-spacing:.08em;
                    border-left:3px solid var(--accent); margin:14px 0 4px 0; }
    table { width:100%; border-collapse:collapse; font-size:11px; }
    th { background:var(--head-bg); color:#7dd3fc; padding:5px 8px;
         text-align:right; white-space:nowrap; font-size:10px;
         letter-spacing:.04em; position:sticky; top:0; }
    th:first-child, th:last-child { text-align:left; }
    td { padding:4px 8px; border-bottom:1px solid var(--border);
         text-align:right; white-space:nowrap; }
    td:first-child { text-align:left; font-weight:600; }
    tr:hover td { background:var(--surface); }
    .pos { color:var(--green); font-weight:600; }
    .neg { color:var(--red);   font-weight:600; }
    .muted { color:var(--muted); }
    .badge { font-size:9px; color:var(--muted); background:var(--surface);
             border:1px solid var(--border); border-radius:3px;
             padding:1px 4px; margin-left:4px; vertical-align:middle; }
    .legend { margin-top:16px; color:var(--muted); font-size:10px; line-height:1.8; }
    .refresh-btn { margin-left:auto; padding:4px 12px; background:var(--surface);
                   color:var(--accent); border:1px solid var(--accent);
                   border-radius:4px; cursor:pointer; font-family:inherit; font-size:11px; }
    .refresh-btn:hover { background:var(--head-bg); }
    .empty { color:var(--muted); padding:20px; text-align:center; }
    .levels { font-size:10px; color:var(--muted); white-space:normal; max-width:200px; }
    .del-btn { background:transparent; border:none; color:var(--red);
               cursor:pointer; font-size:13px; padding:0 4px; line-height:1;
               opacity:0.5; }
    .del-btn:hover { opacity:1; }

    /* ── Add Ticker Panel ── */
    .add-panel { background:var(--surface); border:1px solid var(--border);
                 border-radius:6px; padding:16px; margin-bottom:16px; max-width:540px; }
    .add-panel h2 { font-size:13px; color:var(--accent); margin-bottom:12px; }
    .add-row { display:flex; gap:8px; align-items:flex-end; flex-wrap:wrap; }
    .add-row label { display:flex; flex-direction:column; gap:4px;
                     font-size:10px; color:var(--muted); }
    .add-row input, .add-row select {
      background:var(--bg); border:1px solid var(--border); color:var(--text);
      padding:5px 8px; border-radius:4px; font-family:inherit; font-size:11px;
      width:110px;
    }
    .add-row select { width:180px; }
    .verify-btn { padding:5px 14px; background:var(--head-bg); color:var(--accent);
                  border:1px solid var(--accent); border-radius:4px;
                  cursor:pointer; font-family:inherit; font-size:11px; height:28px; }
    .verify-btn:hover { background:#1e4a7f; }
    .verify-result { margin-top:10px; padding:8px 10px; border-radius:4px;
                     font-size:11px; display:none; }
    .verify-result.ok  { background:#14532d; color:var(--green); border:1px solid #166534; }
    .verify-result.err { background:#450a0a; color:var(--red);   border:1px solid #7f1d1d; }
    .confirm-btn { padding:5px 14px; background:#166534; color:var(--green);
                   border:1px solid var(--green); border-radius:4px;
                   cursor:pointer; font-family:inherit; font-size:11px;
                   margin-top:8px; display:none; }
    .confirm-btn:hover { background:#14532d; }
    .status-msg { margin-top:8px; font-size:11px; color:var(--orange); }
  </style>
</head>
<body>

<header>
  <h1>📊 Market LOI Dashboard</h1>
  <span>{{ date }} &nbsp;|&nbsp; {{ total }} tickers</span>
  <button class="refresh-btn" onclick="location.reload()">↺ Refresh</button>
  <a href="/logout" style="padding:4px 12px;background:var(--surface);color:var(--muted);border:1px solid var(--border);border-radius:4px;text-decoration:none;font-size:11px;white-space:nowrap;">Sign Out</a>
</header>

<div class="tabs">
  <button class="tab active" onclick="showTab('loi',this)">9AM LOIs</button>
  <button class="tab" onclick="showTab('snap',this)">3AM Snapshot</button>
  <button class="tab" onclick="showTab('manage',this)">⚙ Manage Watchlist</button>
</div>

<!-- ── 9AM LOI PANEL ── -->
<div id="panel-loi" class="panel active">
  {% if not loi_rows %}
    <div class="empty">No 8AM LOI data yet for {{ date }}.<br>Check back after 8AM CT.</div>
  {% else %}
    {% for sector, rows in loi_by_sector.items() %}
      <div class="sector-label">{{ sector }}</div>
      <table>
        <thead><tr>
          <th>Ticker</th><th>Last</th><th>Bid</th><th>Ask</th>
          <th>PD High</th><th>PD Low</th><th>PD Close</th>
          <th>PM High</th><th>PM Low</th><th>PM VWAP</th><th>PM Mid</th>
          <th>Gap %</th><th>Round Levels</th>
        </tr></thead>
        <tbody>
          {% for r in rows %}
          <tr>
            <td>{{ r.symbol }}{% if r.is_derived %}<span class="badge">derived</span>{% endif %}</td>
            <td>{{ r.last     | fmt }}</td>
            <td>{{ r.bid      | fmt }}</td>
            <td>{{ r.ask      | fmt }}</td>
            <td>{{ r.pd_high  | fmt }}</td>
            <td>{{ r.pd_low   | fmt }}</td>
            <td>{{ r.pd_close | fmt }}</td>
            <td>{{ r.pm_high  | fmt }}</td>
            <td>{{ r.pm_low   | fmt }}</td>
            <td>{{ r.pm_vwap  | fmt }}</td>
            <td>{{ r.pm_mid   | fmt }}</td>
            <td class="{{ 'pos' if r.gap_pct and r.gap_pct > 0 else 'neg' if r.gap_pct and r.gap_pct < 0 else '' }}">
              {{ r.gap_pct | fmt_pct }}
            </td>
            <td class="levels muted">{{ r.round_levels or '—' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    {% endfor %}
  {% endif %}
</div>

<!-- ── 3AM SNAPSHOT PANEL ── -->
<div id="panel-snap" class="panel">
  {% if not snap_rows %}
    <div class="empty">No 3AM snapshot data yet for {{ date }}.<br>Check back after 3AM CT.</div>
  {% else %}
    {% for sector, rows in snap_by_sector.items() %}
      <div class="sector-label">{{ sector }}</div>
      <table>
        <thead><tr>
          <th>Ticker</th><th>Bid</th><th>Ask</th>
          <th>Spread</th><th>Midpoint</th><th>Last</th><th>Prev Close</th>
        </tr></thead>
        <tbody>
          {% for r in rows %}
          <tr>
            <td>{{ r.symbol }}{% if r.is_derived %}<span class="badge">derived</span>{% endif %}</td>
            <td>{{ r.bid       | fmt }}</td>
            <td>{{ r.ask       | fmt }}</td>
            <td class="muted">{{ r.spread    | fmt(4) }}</td>
            <td>{{ r.midpoint  | fmt }}</td>
            <td>{{ r.last      | fmt }}</td>
            <td class="muted">{{ r.prev_close | fmt }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    {% endfor %}
  {% endif %}
</div>

<!-- ── MANAGE WATCHLIST PANEL ── -->
<div id="panel-manage" class="panel">

  <!-- Add Ticker -->
  <div class="add-panel">
    <h2>➕ Add Ticker</h2>
    <div class="add-row">
      <label>
        Symbol
        <input id="new-symbol" type="text" placeholder="e.g. TSLA" maxlength="10"
               oninput="this.value=this.value.toUpperCase()" onkeydown="if(event.key==='Enter')verifyTicker()">
      </label>
      <label>
        Sector
        <select id="new-sector">
          {% for s in sectors %}
          <option value="{{ s }}">{{ s }}</option>
          {% endfor %}
        </select>
      </label>
      <button class="verify-btn" onclick="verifyTicker()">Verify →</button>
    </div>
    <div id="verify-result" class="verify-result"></div>
    <button id="confirm-btn" class="confirm-btn" onclick="confirmAdd()">
      ✓ Confirm — Add to Watchlist
    </button>
    <div id="status-msg" class="status-msg"></div>
  </div>

  <!-- Current Watchlist -->
  <div class="sector-label" style="margin-top:0">CURRENT WATCHLIST</div>
  {% for sector, rows in watchlist_by_sector.items() %}
    <div class="sector-label" style="border-color:var(--muted);color:var(--muted)">{{ sector }}</div>
    <table>
      <thead><tr>
        <th>Ticker</th><th>Sector</th><th>Type</th><th style="text-align:left">Remove</th>
      </tr></thead>
      <tbody>
        {% for r in rows %}
        <tr id="row-{{ r.symbol }}">
          <td>{{ r.symbol }}</td>
          <td style="text-align:left;color:var(--muted)">{{ r.sector }}</td>
          <td style="text-align:left" class="muted">
            {{ 'derived index' if r.is_derived else 'equity' }}
          </td>
          <td style="text-align:left">
            <button class="del-btn" onclick="deleteTicker('{{ r.symbol }}')"
                    title="Remove {{ r.symbol }}">✕</button>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  {% endfor %}
</div>

<div class="legend">
  PD = Prior Day &nbsp;|&nbsp; PM = Premarket (3AM–8:29AM CT) &nbsp;|&nbsp;
  PM Mid = Midpoint of premarket range &nbsp;|&nbsp; Gap% = PM open vs PD close &nbsp;|&nbsp;
  Derived = cash index (no premarket bid/ask)
</div>

<script>
  // ── Tab switching ───────────────────────────────────────────────────────────
  function showTab(name, btn) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.getElementById('panel-' + name).classList.add('active');
    btn.classList.add('active');
  }

  // ── Verify ticker ───────────────────────────────────────────────────────────
  let verifiedSymbol = null;

  async function verifyTicker() {
    const sym = document.getElementById('new-symbol').value.trim().toUpperCase();
    const resultEl  = document.getElementById('verify-result');
    const confirmEl = document.getElementById('confirm-btn');
    const statusEl  = document.getElementById('status-msg');

    statusEl.textContent = '';
    confirmEl.style.display = 'none';
    verifiedSymbol = null;

    if (!sym) {
      showResult('err', 'Please enter a ticker symbol.');
      return;
    }

    showResult('ok', `Checking ${sym} on Tradier…`);

    try {
      const res  = await fetch(`/api/verify/${sym}`);
      const data = await res.json();

      if (data.valid) {
        showResult('ok',
          `✓ ${data.symbol} — ${data.name} &nbsp;|&nbsp; ` +
          `Exchange: ${data.exchange} &nbsp;|&nbsp; Last: $${data.last}`
        );
        verifiedSymbol = data.symbol;
        confirmEl.style.display = 'inline-block';
      } else {
        showResult('err', `✗ ${data.error}`);
      }
    } catch(e) {
      showResult('err', 'Network error — try again.');
    }
  }

  function showResult(type, msg) {
    const el = document.getElementById('verify-result');
    el.className = `verify-result ${type}`;
    el.innerHTML = msg;
    el.style.display = 'block';
  }

  // ── Confirm add ─────────────────────────────────────────────────────────────
  async function confirmAdd() {
    if (!verifiedSymbol) return;
    const sector   = document.getElementById('new-sector').value;
    const statusEl = document.getElementById('status-msg');

    statusEl.textContent = `Adding ${verifiedSymbol}…`;

    try {
      const res  = await fetch('/api/watchlist/add', {
        method:  'POST',
        headers: {'Content-Type': 'application/json'},
        body:    JSON.stringify({symbol: verifiedSymbol, sector: sector}),
      });
      const data = await res.json();

      if (data.ok) {
        statusEl.textContent = `✓ ${verifiedSymbol} added to ${sector}. Reload to see it.`;
        document.getElementById('confirm-btn').style.display = 'none';
        document.getElementById('verify-result').style.display = 'none';
        document.getElementById('new-symbol').value = '';
        verifiedSymbol = null;
      } else {
        statusEl.textContent = `✗ ${data.error}`;
      }
    } catch(e) {
      statusEl.textContent = 'Network error — try again.';
    }
  }

  // ── Delete ticker ───────────────────────────────────────────────────────────
  async function deleteTicker(symbol) {
    if (!confirm(`Remove ${symbol} from the watchlist?`)) return;

    try {
      const res  = await fetch(`/api/watchlist/remove/${symbol}`, {method: 'POST'});
      const data = await res.json();

      if (data.ok) {
        const row = document.getElementById(`row-${symbol}`);
        if (row) row.remove();
      } else {
        alert(`Could not remove ${symbol}: ${data.error}`);
      }
    } catch(e) {
      alert('Network error — try again.');
    }
  }
</script>
</body>
</html>
"""


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.template_filter("fmt")
def fmt_filter(val, decimals=2):
    return fmt_val(val, decimals)

@app.template_filter("fmt_pct")
def fmt_pct_filter(val):
    return fmt_pct(val)


LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Market LOI — Login</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0f172a; color: #e2e8f0;
           font-family: 'Courier New', monospace;
           display: flex; align-items: center; justify-content: center;
           min-height: 100vh; }
    .card { background: #1e293b; border: 1px solid #334155;
            border-radius: 8px; padding: 32px; width: 320px; }
    h1 { font-size: 16px; color: #38bdf8; margin-bottom: 6px; }
    p  { font-size: 11px; color: #94a3b8; margin-bottom: 24px; }
    label { font-size: 10px; color: #94a3b8; display: block; margin-bottom: 4px; }
    input { width: 100%; background: #0f172a; border: 1px solid #334155;
            color: #e2e8f0; padding: 8px 10px; border-radius: 4px;
            font-family: inherit; font-size: 12px; margin-bottom: 16px; }
    input:focus { outline: none; border-color: #38bdf8; }
    button { width: 100%; padding: 8px; background: #1e3a5f;
             color: #38bdf8; border: 1px solid #38bdf8; border-radius: 4px;
             cursor: pointer; font-family: inherit; font-size: 12px; }
    button:hover { background: #1e4a7f; }
    .error { color: #f87171; font-size: 11px; margin-bottom: 12px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>📊 Market LOI Dashboard</h1>
    <p>Enter your password to continue.</p>
    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}
    <form method="POST" action="/login">
      <label>Password</label>
      <input type="password" name="password" autofocus
             placeholder="••••••••••••">
      <button type="submit">Sign In →</button>
    </form>
  </div>
</body>
</html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        return render_template_string(LOGIN_HTML, error="Incorrect password.")
    return render_template_string(LOGIN_HTML, error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    today     = datetime.now(CT).strftime("%Y-%m-%d")
    loi_rows  = fetch_latest("lois_9am",     today)
    snap_rows = fetch_latest("snapshots_4am", today)
    watchlist = get_watchlist()

    return render_template_string(
        DASHBOARD_HTML,
        date              = today,
        total             = len(watchlist),
        loi_rows          = loi_rows,
        snap_rows         = snap_rows,
        loi_by_sector     = group_by_sector(loi_rows),
        snap_by_sector    = group_by_sector(snap_rows),
        watchlist_by_sector = group_by_sector(watchlist),
        sectors           = SECTORS,
    )


@app.route("/api/verify/<symbol>")
@api_auth_required
def api_verify(symbol):
    """Verify a ticker against Tradier and check it's not already in watchlist."""
    result = verify_ticker(symbol.upper())
    if result["valid"] and ticker_exists_in_watchlist(symbol):
        result["valid"] = False
        result["error"] = f"{symbol.upper()} is already in your watchlist"
    return jsonify(result)


@app.route("/api/watchlist/add", methods=["POST"])
@api_auth_required
def api_add():
    data   = request.get_json()
    symbol = (data.get("symbol") or "").upper().strip()
    sector = (data.get("sector") or "Other").strip()

    if not symbol:
        return jsonify({"ok": False, "error": "No symbol provided"})

    check = verify_ticker(symbol)
    if not check["valid"]:
        return jsonify({"ok": False, "error": check["error"]})

    if ticker_exists_in_watchlist(symbol):
        return jsonify({"ok": False, "error": f"{symbol} is already in watchlist"})

    ok = add_ticker(symbol, sector)
    if ok:
        return jsonify({"ok": True, "symbol": symbol, "sector": sector})
    return jsonify({"ok": False, "error": "Database write failed — check logs"})


@app.route("/api/watchlist/remove/<symbol>", methods=["POST"])
@api_auth_required
def api_remove(symbol):
    ok = remove_ticker(symbol.upper())
    if ok:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Could not remove ticker — check logs"})


@app.route("/api/loi/<date>")
@api_auth_required
def api_loi(date):
    return jsonify(fetch_latest("lois_9am", date))


@app.route("/api/snapshot/<date>")
@api_auth_required
def api_snapshot(date):
    return jsonify(fetch_latest("snapshots_4am", date))

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now(CT).isoformat()})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
