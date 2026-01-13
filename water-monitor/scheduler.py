"""
Scheduler for automated water meter scraping and alerts.

Runs:
- Hourly: Scrape all meter accounts
- Daily (6 AM): Send daily summary email
- After each scrape: Check alert conditions
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging
import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def hourly_scrape_job():
    """Run hourly scrape of all accounts."""
    logger.info("Starting hourly scrape job")
    try:
        from scraper import run_scrape
        results = run_scrape()
        logger.info(f"Hourly scrape complete: {results['success']} success, {results['failed']} failed")

        # Check alerts after scraping
        check_alerts_job()

    except Exception as e:
        logger.error(f"Hourly scrape failed: {e}")


def check_alerts_job():
    """Check all alert conditions."""
    logger.info("Checking alert conditions")
    try:
        from alerts import process_alerts
        triggered = process_alerts()
        if triggered:
            logger.warning(f"Triggered {len(triggered)} alerts")
            for alert in triggered:
                logger.warning(f"  Alert: {alert['building']} {alert['unit']} - {alert['type']}: {alert['message']}")
        else:
            logger.info("No alerts triggered")
    except Exception as e:
        logger.error(f"Alert check failed: {e}")


def daily_summary_job():
    """Send daily summary email."""
    logger.info("Sending daily summary")
    try:
        from alerts import send_daily_summary
        send_daily_summary()
        logger.info("Daily summary sent")
    except Exception as e:
        logger.error(f"Daily summary failed: {e}")


def create_scheduler() -> BackgroundScheduler:
    """Create and configure the scheduler."""
    scheduler = BackgroundScheduler()

    # Hourly scrape (at minute 0 of every hour)
    scheduler.add_job(
        hourly_scrape_job,
        CronTrigger(minute=0),  # Every hour at :00
        id='hourly_scrape',
        name='Hourly meter scrape',
        replace_existing=True
    )

    # Daily summary at 6 AM
    scheduler.add_job(
        daily_summary_job,
        CronTrigger(hour=6, minute=0),  # 6:00 AM daily
        id='daily_summary',
        name='Daily summary email',
        replace_existing=True
    )

    return scheduler


def run_scheduler():
    """Run the scheduler standalone."""
    logger.info("Starting Water Monitor Scheduler")

    scheduler = create_scheduler()
    scheduler.start()

    logger.info("Scheduler started. Jobs scheduled:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name}: {job.trigger}")

    # Keep running
    try:
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler")
        scheduler.shutdown()


if __name__ == "__main__":
    run_scheduler()
