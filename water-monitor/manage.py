#!/usr/bin/env python3
"""
Water Monitor Management CLI

Usage:
    python manage.py init                    - Initialize database
    python manage.py add_account             - Add a new account interactively
    python manage.py import_accounts FILE    - Import accounts from CSV
    python manage.py list_accounts           - List all accounts
    python manage.py scrape                  - Run scrape now
    python manage.py inspect EMAIL PASSWORD  - Inspect site structure (for debugging)
    python manage.py genkey                  - Generate encryption key
    python manage.py run                     - Run web app + scheduler
"""

import sys
import csv
from cryptography.fernet import Fernet


def cmd_init():
    """Initialize the database."""
    import database as db
    db.init_db()
    print("Database initialized.")


def cmd_genkey():
    """Generate a new encryption key."""
    key = Fernet.generate_key().decode()
    print(f"Generated encryption key:")
    print(f"  {key}")
    print(f"\nAdd this to your .env file:")
    print(f"  ENCRYPTION_KEY={key}")


def cmd_add_account():
    """Add an account interactively."""
    import database as db

    print("Add New Meter Account")
    print("-" * 40)

    building = input("Building name: ").strip()
    unit = input("Unit number: ").strip()
    email = input("Email (mywateradvisor2.com login): ").strip()
    password = input("Password: ").strip()

    if not email or not password:
        print("Error: Email and password are required")
        return

    try:
        account_id = db.add_account(email, password, building, unit)
        print(f"\nAccount added successfully (ID: {account_id})")
    except Exception as e:
        print(f"Error: {e}")


def cmd_import_accounts(filename):
    """Import accounts from CSV file."""
    import database as db

    print(f"Importing accounts from {filename}")

    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        errors = 0

        for row in reader:
            try:
                email = row.get('email', '').strip()
                password = row.get('password', '').strip()
                building = row.get('building_name', '').strip()
                unit = row.get('unit_number', '').strip()
                account_number = row.get('account_number', '').strip()
                address = row.get('address', '').strip()

                if not email or not password:
                    print(f"  Skipping row - missing email or password")
                    errors += 1
                    continue

                db.add_account(email, password, building, unit, account_number, address)
                count += 1
                print(f"  Added: {building} - {unit} ({address}) - Account: {account_number}")

            except Exception as e:
                print(f"  Error: {e}")
                errors += 1

    print(f"\nImport complete: {count} added, {errors} errors")


def cmd_list_accounts():
    """List all accounts."""
    import database as db

    accounts = db.get_all_accounts()

    if not accounts:
        print("No accounts configured.")
        return

    print(f"{'ID':<4} {'Building':<20} {'Unit':<6} {'Address':<20} {'Account #':<15} {'Last Scraped':<20}")
    print("-" * 95)

    for a in accounts:
        last = a['last_scraped'][:16] if a['last_scraped'] else 'Never'
        print(f"{a['id']:<4} {(a['building_name'] or '-')[:18]:<20} {(a['unit_number'] or '-')[:5]:<6} {(a['address'] or '-')[:18]:<20} {(a['account_number'] or '-')[:13]:<15} {last:<20}")


def cmd_scrape():
    """Run scrape manually."""
    from scraper import run_scrape
    print("Starting scrape of all accounts...")
    results = run_scrape()
    print(f"Complete: {results['success']} successful, {results['failed']} failed")


def cmd_inspect(email, password):
    """Inspect the site structure for debugging."""
    from scraper import inspect_site
    print(f"Inspecting site with account {email}...")
    result = inspect_site(email, password)
    print(result)


def cmd_run():
    """Run the web app with scheduler."""
    import threading
    from app import app
    from scheduler import create_scheduler
    import database as db

    # Initialize database
    db.init_db()

    # Start scheduler in background
    scheduler = create_scheduler()
    scheduler.start()
    print("Scheduler started")

    # Run Flask app
    print("Starting web server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == 'init':
        cmd_init()
    elif cmd == 'genkey':
        cmd_genkey()
    elif cmd == 'add_account':
        cmd_add_account()
    elif cmd == 'import_accounts':
        if len(sys.argv) < 3:
            print("Usage: python manage.py import_accounts FILE.csv")
            return
        cmd_import_accounts(sys.argv[2])
    elif cmd == 'list_accounts':
        cmd_list_accounts()
    elif cmd == 'scrape':
        cmd_scrape()
    elif cmd == 'inspect':
        if len(sys.argv) < 4:
            print("Usage: python manage.py inspect EMAIL PASSWORD")
            return
        cmd_inspect(sys.argv[2], sys.argv[3])
    elif cmd == 'run':
        cmd_run()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
