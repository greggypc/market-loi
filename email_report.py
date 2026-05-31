"""
Email Report
────────────
Two emails per morning:
  1. 3AM CT — bid/ask snapshot at premarket open
  2. 8AM CT — full LOI report before market open

Uses Gmail SMTP with an App Password.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER

logger = logging.getLogger(__name__)


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _fmt(val, decimals=2):
    if val is None:
        return "—"
    try:
        return f"{float(val):.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def _gap_cell(gap_pct):
    if gap_pct is None:
        return "<td>—</td>"
    val   = float(gap_pct)
    sign  = "+" if val >= 0 else ""
    color = "#16a34a" if val >= 0 else "#dc2626"
    return f'<td style="color:{color};font-weight:600">{sign}{val:.2f}%</td>'


BASE_STYLE = """
    body  { font-family: 'Courier New', monospace; font-size: 12px;
            background: #0f172a; color: #e2e8f0; margin: 0; padding: 16px; }
    h1    { font-size: 16px; color: #38bdf8; margin: 0 0 4px 0; }
    p     { margin: 0 0 12px 0; color: #94a3b8; font-size: 11px; }
    table { border-collapse: collapse; width: 100%; font-size: 11px; }
    th    { background: #1e3a5f; color: #7dd3fc; padding: 5px 8px;
            text-align: left; white-space: nowrap; font-size: 10px;
            letter-spacing: .04em; }
    td    { padding: 4px 8px; border-bottom: 1px solid #1e293b;
            white-space: nowrap; }
    tr:hover td { background: #1e293b; }
    .sector { background: #1e293b; color: #f1f5f9; font-weight: 700;
              padding: 6px 10px; font-size: 13px; letter-spacing: .05em; }
    .muted  { font-size: 10px; color: #6b7280; }
"""


def _send(subject: str, html: str):
    """Shared SMTP send — used by both report types."""
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        logger.warning("Email credentials not set — skipping")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVER
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        logger.info(f"Email sent → {EMAIL_RECEIVER} | {subject}")
    except Exception as e:
        logger.error(f"Email send failed: {e}")


def _sector_sections(rows: list, row_fn) -> str:
    """Build sector-grouped table rows, ordered by sector as returned from DB."""
    # Preserve sector order as it appears in the rows (already sorted by Supabase)
    seen_sectors = []
    by_sector = {}
    for r in rows:
        s = r.get("sector", "Other")
        if s not in by_sector:
            seen_sectors.append(s)
            by_sector[s] = []
        by_sector[s].append(r)

    html = ""
    for sector_name in seen_sectors:
        sector_rows = by_sector[sector_name]
        if not sector_rows:
            continue
        html += f'<tr><td colspan="99" class="sector">{sector_name.upper()}</td></tr>'
        for r in sector_rows:
            html += row_fn(r)
        html += '<tr><td colspan="99" style="height:6px"></td></tr>'
    return html


# ── Email 1 — 3AM Snapshot ────────────────────────────────────────────────────

def _snapshot_row(r: dict) -> str:
    derived = '<span class="muted"> [derived]</span>' if r.get("is_derived") else ""
    spread_color = ""
    if r.get("spread") is not None:
        spread_color = "color:#f87171" if float(r["spread"]) > 0.10 else "color:#4ade80"
    return f"""
    <tr>
      <td style="font-weight:600">{r['symbol']}{derived}</td>
      <td>{_fmt(r.get('bid'))}</td>
      <td>{_fmt(r.get('ask'))}</td>
      <td style="{spread_color}">{_fmt(r.get('spread'), 4)}</td>
      <td>{_fmt(r.get('midpoint'))}</td>
      <td>{_fmt(r.get('last'))}</td>
      <td class="muted">{_fmt(r.get('prev_close'))}</td>
    </tr>"""


def build_snapshot_html(rows: list[dict], snap_date: str) -> str:
    sections = _sector_sections(rows, _snapshot_row)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head>
<body>
  <h1>🌅 3AM Snapshot — {snap_date}</h1>
  <p>Captured at 3:00AM CT (premarket open) &nbsp;|&nbsp; {len(rows)} tickers</p>
  <table>
    <thead>
      <tr>
        <th>Ticker</th><th>Bid</th><th>Ask</th>
        <th>Spread</th><th>Midpoint</th><th>Last</th><th>Prev Close</th>
      </tr>
    </thead>
    <tbody>{sections}</tbody>
  </table>
  <p style="margin-top:12px;font-size:10px;color:#475569">
    Spread highlighted red if &gt; $0.10 &nbsp;|&nbsp;
    Derived = cash index, no premarket bid/ask
  </p>
</body></html>"""


def send_snapshot_report(rows: list[dict], snap_date: str):
    html = build_snapshot_html(rows, snap_date)
    _send(f"3AM Snapshot {snap_date}", html)


# ── Email 2 — 8AM LOI Report ──────────────────────────────────────────────────

def _loi_row(r: dict) -> str:
    derived = '<span class="muted"> [derived]</span>' if r.get("is_derived") else ""
    gap_pct = r.get("gap_pct")
    if gap_pct is not None:
        val   = float(gap_pct)
        sign  = "+" if val >= 0 else ""
        color = "#16a34a" if val >= 0 else "#dc2626"
        gap_td = f'<td style="color:{color};font-weight:600">{sign}{val:.2f}%</td>'
    else:
        gap_td = "<td>—</td>"

    return f"""
    <tr>
      <td style="font-weight:600">{r['symbol']}{derived}</td>
      <td>{_fmt(r.get('last'))}</td>
      <td>{_fmt(r.get('bid'))}</td>
      <td>{_fmt(r.get('ask'))}</td>
      <td>{_fmt(r.get('pd_high'))}</td>
      <td>{_fmt(r.get('pd_low'))}</td>
      <td>{_fmt(r.get('pd_close'))}</td>
      <td>{_fmt(r.get('pm_high'))}</td>
      <td>{_fmt(r.get('pm_low'))}</td>
      <td>{_fmt(r.get('pm_vwap'))}</td>
      <td>{_fmt(r.get('pm_mid'))}</td>
      {gap_td}
      <td class="muted" style="font-size:10px">{r.get('round_levels','—')}</td>
    </tr>"""


def build_loi_html(rows: list[dict], snap_date: str) -> str:
    sections = _sector_sections(rows, _loi_row)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head>
<body>
  <h1>📊 8AM LOI Report — {snap_date}</h1>
  <p>Generated at 8:00AM CT (30 min before open) &nbsp;|&nbsp; {len(rows)} tickers</p>
  <table>
    <thead>
      <tr>
        <th>Ticker</th><th>Last</th><th>Bid</th><th>Ask</th>
        <th>PD High</th><th>PD Low</th><th>PD Close</th>
        <th>PM High</th><th>PM Low</th><th>PM VWAP</th><th>PM Mid</th>
        <th>Gap%</th><th>Round Levels</th>
      </tr>
    </thead>
    <tbody>{sections}</tbody>
  </table>
  <p style="margin-top:12px;font-size:10px;color:#475569">
    PD = Prior Day &nbsp;|&nbsp; PM = Premarket (3AM–8:29AM CT) &nbsp;|&nbsp;
    PM Mid = midpoint of premarket range &nbsp;|&nbsp; Gap% = PM open vs PD close
  </p>
</body></html>"""


def send_report(rows: list[dict], snap_date: str):
    """Called by job_9am — sends the 8AM LOI email."""
    html = build_loi_html(rows, snap_date)
    _send(f"LOI Report {snap_date}", html)
