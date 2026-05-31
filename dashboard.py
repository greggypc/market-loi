"""
Web Dashboard
─────────────
Lightweight Flask app that serves today's 4AM snapshot and 9AM LOI data.
Hosted on Railway at a public URL.
"""

import logging
from datetime import datetime, date
from zoneinfo import ZoneInfo
from flask import Flask, render_template_string, jsonify
from db import fetch_latest, fetch_recent_days
from config import WATCHLIST

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CT  = ZoneInfo("America/Chicago")


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Market LOI Dashboard — {{ date }}</title>
  <style>
    :root {
      --bg:      #0f172a;
      --surface: #1e293b;
      --border:  #334155;
      --text:    #e2e8f0;
      --muted:   #94a3b8;
      --accent:  #38bdf8;
      --green:   #4ade80;
      --red:     #f87171;
      --head-bg: #1e3a5f;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg); color: var(--text);
      font-family: 'Courier New', monospace; font-size: 12px;
      padding: 16px;
    }
    header {
      display: flex; align-items: baseline; gap: 16px;
      border-bottom: 1px solid var(--border); padding-bottom: 10px;
      margin-bottom: 16px;
    }
    header h1 { font-size: 18px; color: var(--accent); }
    header span { color: var(--muted); font-size: 11px; }
    .tabs {
      display: flex; gap: 8px; margin-bottom: 12px;
    }
    .tab {
      padding: 5px 14px; border-radius: 4px; cursor: pointer;
      background: var(--surface); color: var(--muted);
      border: 1px solid var(--border); font-size: 11px;
      font-family: inherit;
    }
    .tab.active { background: var(--head-bg); color: var(--accent);
                  border-color: var(--accent); }
    .panel { display: none; }
    .panel.active { display: block; }
    .sector-label {
      background: var(--surface);
      color: var(--accent);
      font-weight: 700;
      padding: 5px 10px;
      font-size: 11px;
      letter-spacing: .08em;
      border-left: 3px solid var(--accent);
      margin: 14px 0 4px 0;
    }
    table {
      width: 100%; border-collapse: collapse;
      font-size: 11px;
    }
    th {
      background: var(--head-bg); color: #7dd3fc;
      padding: 5px 8px; text-align: right;
      white-space: nowrap; font-size: 10px;
      letter-spacing: .04em; position: sticky; top: 0;
    }
    th:first-child { text-align: left; }
    td {
      padding: 4px 8px; border-bottom: 1px solid var(--border);
      text-align: right; white-space: nowrap;
    }
    td:first-child { text-align: left; font-weight: 600; }
    tr:hover td { background: var(--surface); }
    .pos { color: var(--green); font-weight: 600; }
    .neg { color: var(--red);   font-weight: 600; }
    .muted { color: var(--muted); }
    .badge {
      font-size: 9px; color: var(--muted);
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 3px; padding: 1px 4px;
      margin-left: 4px; vertical-align: middle;
    }
    .legend {
      margin-top: 16px; color: var(--muted);
      font-size: 10px; line-height: 1.8;
    }
    .refresh-btn {
      margin-left: auto; padding: 4px 12px;
      background: var(--surface); color: var(--accent);
      border: 1px solid var(--accent); border-radius: 4px;
      cursor: pointer; font-family: inherit; font-size: 11px;
    }
    .refresh-btn:hover { background: var(--head-bg); }
    .empty { color: var(--muted); padding: 20px; text-align: center; }
    .levels { font-size: 10px; color: var(--muted); max-width: 200px;
              white-space: normal; }
  </style>
</head>
<body>
  <header>
    <h1>📊 Market LOI Dashboard</h1>
    <span>{{ date }} &nbsp;|&nbsp; {{ total }} tickers</span>
    <button class="refresh-btn" onclick="location.reload()">↺ Refresh</button>
  </header>

  <div class="tabs">
    <button class="tab active" onclick="showTab('loi')">9AM LOIs</button>
    <button class="tab" onclick="showTab('snap')">4AM Snapshot</button>
  </div>

  <!-- 9AM LOI PANEL -->
  <div id="panel-loi" class="panel active">
    {% if not loi_rows %}
      <div class="empty">No 9AM LOI data yet for {{ date }}.<br>
        Check back after 9AM CT.</div>
    {% else %}
      {% for sector, rows in loi_by_sector.items() %}
        <div class="sector-label">{{ sector }}</div>
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Last</th>
              <th>Bid</th>
              <th>Ask</th>
              <th>PD High</th>
              <th>PD Low</th>
              <th>PD Close</th>
              <th>PM High</th>
              <th>PM Low</th>
              <th>PM VWAP</th>
              <th>PM Mid</th>
              <th>Gap %</th>
              <th>Round Levels</th>
            </tr>
          </thead>
          <tbody>
            {% for r in rows %}
            <tr>
              <td>
                {{ r.symbol }}
                {% if r.is_derived %}
                  <span class="badge">derived</span>
                {% endif %}
              </td>
              <td>{{ r.last | fmt }}</td>
              <td>{{ r.bid  | fmt }}</td>
              <td>{{ r.ask  | fmt }}</td>
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

  <!-- 4AM SNAPSHOT PANEL -->
  <div id="panel-snap" class="panel">
    {% if not snap_rows %}
      <div class="empty">No 4AM snapshot data yet for {{ date }}.<br>
        Check back after 4AM CT.</div>
    {% else %}
      {% for sector, rows in snap_by_sector.items() %}
        <div class="sector-label">{{ sector }}</div>
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Bid</th>
              <th>Ask</th>
              <th>Spread</th>
              <th>Midpoint</th>
              <th>Last</th>
              <th>Prev Close</th>
            </tr>
          </thead>
          <tbody>
            {% for r in rows %}
            <tr>
              <td>
                {{ r.symbol }}
                {% if r.is_derived %}
                  <span class="badge">derived</span>
                {% endif %}
              </td>
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

  <div class="legend">
    PD = Prior Day &nbsp;|&nbsp;
    PM = Premarket (3AM–8:29AM CT) &nbsp;|&nbsp;
    PM Mid = Midpoint of premarket range &nbsp;|&nbsp;
    Gap% = PM open vs PD close &nbsp;|&nbsp;
    Derived = cash index (no premarket bid/ask)
  </div>

  <script>
    function showTab(name) {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      document.getElementById('panel-' + name).classList.add('active');
      event.target.classList.add('active');
    }
  </script>
</body>
</html>
"""


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
        v = float(val)
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:.2f}%"
    except (TypeError, ValueError):
        return "—"


def group_by_sector(rows: list[dict]) -> dict:
    """Group rows by sector preserving WATCHLIST order."""
    grouped = {s: [] for s in WATCHLIST}
    for row in rows:
        s = row.get("sector", "Other")
        if s in grouped:
            grouped[s].append(row)
        else:
            grouped.setdefault("Other", []).append(row)
    # Remove empty sectors
    return {k: v for k, v in grouped.items() if v}


@app.template_filter("fmt")
def fmt_filter(val, decimals=2):
    return fmt_val(val, decimals)


@app.template_filter("fmt_pct")
def fmt_pct_filter(val):
    return fmt_pct(val)


@app.route("/")
def dashboard():
    today = datetime.now(CT).strftime("%Y-%m-%d")

    loi_rows  = fetch_latest("lois_9am",      today)
    snap_rows = fetch_latest("snapshots_4am",  today)

    return render_template_string(
        DASHBOARD_HTML,
        date          = today,
        total         = len(set(r["symbol"] for r in loi_rows + snap_rows)),
        loi_rows      = loi_rows,
        snap_rows     = snap_rows,
        loi_by_sector = group_by_sector(loi_rows),
        snap_by_sector= group_by_sector(snap_rows),
    )


@app.route("/api/loi/<date>")
def api_loi(date):
    return jsonify(fetch_latest("lois_9am", date))


@app.route("/api/snapshot/<date>")
def api_snapshot(date):
    return jsonify(fetch_latest("snapshots_4am", date))


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now(CT).isoformat()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
