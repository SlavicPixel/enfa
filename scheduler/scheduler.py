"""
Standalone scheduler — runs as a separate process (or Docker container).
Calls the same pipeline functions as the on-demand refresh.
"""

import os
import sys
import time
import django
from datetime import datetime

# Bootstrap Django so we can use settings + models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BlockingScheduler(timezone="UTC")


def news_job():
    print(f"[{datetime.now()}] Running news refresh...")
    from dashboard.pipeline import get_db, refresh_news
    refresh_news(get_db())


def prices_job():
    print(f"[{datetime.now()}] Running price + feature refresh...")
    from dashboard.pipeline import get_db, refresh_prices, refresh_features
    db = get_db()
    refresh_prices(db)
    refresh_features(db)


# News every day at 08:00 UTC
scheduler.add_job(news_job,   CronTrigger(hour=8,  minute=0))
# Prices every weekday at 22:00 UTC (after US market close)
scheduler.add_job(prices_job, CronTrigger(hour=22, minute=0,
                                          day_of_week="mon-fri"))

if __name__ == "__main__":
    print("Scheduler started. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")