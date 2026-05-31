"""
Email Report
────────────
Sends a clean, scannable HTML email with the 9AM LOI snapshot.
Uses Gmail SMTP with an App Password.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER, WATCHLIST

logger = logging.getLogger(__name__)


def _fmt(val, decimals=2, prefix="", suffix=""):
    if val is None:
        return "—"
    try:
        return f"{prefix}{float(val):.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def _gap_cell(gap_pct):
    if gap_pct is None:
        return "<td>—</td>"
    val  = float(gap_pct)
    sign = "+" if val >= 0 else ""
    color = "#16a34a" if val >= 0 else "#dc2626"  # green / red
    return f'<td style="color:{color};font-weight:600">{sign}{val:.2f}%</td>'


def build_html(rows: list[dict], snap_date: str) -> str:
    # Index rows into dict for quick lookup
    by_symbol = {r["symbol"]: r for r in rows}

    sections_html = ""

    for sector_name, sector_data in WATCHLIST.items():
        tickers = sector_data["tickers"]
        sector_rows = [by_symbol[t] for t in tickers if t in by_symbol]
        if not sector_rows:
            continue

        rows_html = ""
        for r in sector_rows:
            note_badge = (
                f'<span style="font-size:10px;color:#6b7280;margin-left:4px">'
                f'[{r["note"]}]</span>'
                if r.get("note") else ""
            )
            rows_html += f"""
            <tr>
              <td style="font-weight:600;white-space:nowrap">
                {r['symbol']}{note_badge}
              </td>
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
              {_gap_cell(r.get('gap_pct'))}
              <td style="font-size:11px;color:#6b7280">{r.get('round_levels','—')}</td>
            </tr>"""

        sections_html += f"""
        <tr>
          <td colspan="13"
              style="background:#1e293b;color:#f1f5f9;font-weight:700;
                     padding:6px 10px;font-size:13px;letter-spacing:.05em">
            {sector_name.upper()}
          </td>
        </tr>
        {rows_html}
        <tr><td colspan="13" style="height:6px"></td></tr>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body  {{ font-family: 'Courier New', monospace; font-size: 12px;
             background: #0f172a; color: #e2e8f0; margin: 0; padding: 16px; }}
    h1    {{ font-size: 16px; color: #38bdf8; margin: 0 0 4px 0; }}
    p     {{ margin: 0 0 12px 0; color: #94a3b8; font-size: 11px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 11px; }}
    th    {{ background: #1e3a5f; color: #7dd3fc; padding: 5px 8px;
             text-align: left; white-space: nowrap; font-size: 10px;
             letter-spacing: .04em; }}
    td    {{ padding: 4px 8px; border-bottom: 1px solid #1e293b;
             white-space: nowrap; }}
    tr:hover td {{ background: #1e293b; }}
  </style>
</head>
<body>
  <h1>📊 Morning LOI Report — {snap_date}</h1>
  <p>Generated at 8:00AM CT &nbsp;|&nbsp; {len(rows)} tickers</p>
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
        <th>Gap%</th>
        <th>Round Levels</th>
      </tr>
    </thead>
    <tbody>
      {sections_html}
    </tbody>
  </table>
  <p style="margin-top:12px;font-size:10px;color:#475569">
    PD = Prior Day &nbsp;|&nbsp; PM = Premarket (3AM–8:29AM CT) &nbsp;|&nbsp;
    PM Mid = midpoint of premarket range &nbsp;|&nbsp;
    Gap% = PM open vs PD close
  </p>
</body>
</html>
"""


def send_report(rows: list[dict], snap_date: str):
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        logger.warning("Email credentials not set — skipping email report")
        return

    subject = f"LOI Report {snap_date}"
    html    = build_html(rows, snap_date)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVER
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        logger.info(f"Email report sent to {EMAIL_RECEIVER}")
    except Exception as e:
        logger.error(f"Email send failed: {e}")
