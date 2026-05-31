"""
Scheduler — main entry point for Railway
──────────────────────────────────────────
Runs the Flask dashboard AND the two scheduled jobs in one process.
  4:00AM CT → 4AM bid/ask snapshot
  9:00AM CT → 9AM LOI + email report

Railway starts this file via: python main.py
"""

import logging
import threading
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from job_4am import run_4am_snapshot
from job_9am import run_9am_loi
from dashboard import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

CT = ZoneInfo("America/Chicago")


def start_scheduler():
    scheduler = BackgroundScheduler(timezone="America/Chicago")

    # 3:00AM CT (= 4AM ET) — bid/ask snapshot at premarket open
    scheduler.add_job(
        run_4am_snapshot,
        CronTrigger(hour=3, minute=0, timezone="America/Chicago"),
        id="snapshot_4am",
        name="3AM CT Bid/Ask Snapshot",
        misfire_grace_time=300,  # allow 5-min late start
    )

    # 8:00AM CT (= 9AM ET) — LOI calculation + email, 30 min before open
    scheduler.add_job(
        run_9am_loi,
        CronTrigger(hour=8, minute=0, timezone="America/Chicago"),
        id="loi_9am",
        name="8AM CT LOI + Email Report",
        misfire_grace_time=300,
    )

    scheduler.start()
    logger.info("Scheduler started — jobs: 3AM CT snapshot | 8AM CT LOI+email")
    return scheduler


if __name__ == "__main__":
    scheduler = start_scheduler()

    # Run Flask dashboard on the main thread
    # Railway injects PORT env var; default 8080
    import os
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Dashboard starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
