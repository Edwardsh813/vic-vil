#!/usr/bin/env python3
"""
Victorian Village - Innago/UISP Integration Service

Syncs tenant data from Innago to UISP for automated fiber service provisioning.
"""

import argparse
import logging
import signal
import sys
import time

import schedule

from src.config import Config
from src.sync import SyncEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("vic-vil-sync.log")
    ]
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Victorian Village Innago/UISP Integration")
    parser.add_argument("-c", "--config", default="config.yaml", help="Config file path")
    parser.add_argument("--once", action="store_true", help="Run once and exit (no scheduling)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run - don't make changes")
    args = parser.parse_args()

    try:
        config = Config(args.config)
    except FileNotFoundError as e:
        logger.error(f"Config error: {e}")
        logger.error("Copy config.example.yaml to config.yaml and fill in your values")
        sys.exit(1)

    engine = SyncEngine(config)

    if args.once:
        logger.info("Running single sync...")
        engine.run_sync()
        logger.info("Done.")
        return

    # Set up scheduled runs
    interval = config.polling_interval
    logger.info(f"Starting scheduler - running every {interval} minutes")

    schedule.every(interval).minutes.do(engine.run_sync)

    # Run immediately on start
    engine.run_sync()

    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run scheduler loop
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
