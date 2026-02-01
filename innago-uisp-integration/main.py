#!/usr/bin/env python3
"""
Victorian Village - Innago/UISP Integration Service

Simplified billing model:
- ERE invoices apartment complex monthly based on occupied units
- Internet is included in rent
- ONU activated when lease starts, suspended when it ends
- ONU suspended if rent not paid by 5th
- Internet tickets forwarded to UISP
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
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--billing", action="store_true", help="Generate billing report")
    parser.add_argument("--invoice", action="store_true", help="Generate billing + create UISP invoice")
    parser.add_argument("--status", action="store_true", help="Show current unit status")
    args = parser.parse_args()

    try:
        config = Config(args.config)
    except FileNotFoundError as e:
        logger.error(f"Config error: {e}")
        sys.exit(1)

    engine = SyncEngine(config)

    # Billing report mode
    if args.billing or args.invoice:
        report = engine.print_billing_report(create_invoice=args.invoice)
        return

    # Status mode
    if args.status:
        print_status(engine)
        return

    # Single run mode
    if args.once:
        logger.info("Running single sync...")
        engine.run_sync()
        logger.info("Done.")
        return

    # Scheduled mode
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


def print_status(engine):
    """Print current unit status."""
    active = engine.db.get_active_units()
    delinquent = engine.db.get_delinquent_units()

    print(f"""
Victorian Village - Unit Status
{'=' * 40}
Total Units:      118
Occupied:         {len(active)}
Vacant:           {118 - len(active)}
Delinquent:       {len(delinquent)}
{'=' * 40}
""")

    if delinquent:
        print("Delinquent Units:")
        for u in delinquent:
            print(f"  - Unit {u['unit_number']}")
        print()


if __name__ == "__main__":
    main()
