"""
Database for Victorian Village integration.

Simplified schema - tracks units, not complex tenant relationships.
"""

import sqlite3
from pathlib import Path
from datetime import datetime


class Database:
    def __init__(self, db_path: str = "vic_vil_sync.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Units table - tracks occupancy and ONU status
            conn.execute("""
                CREATE TABLE IF NOT EXISTS units (
                    unit_number TEXT PRIMARY KEY,
                    lease_id TEXT,
                    property_address TEXT,
                    status TEXT DEFAULT 'vacant',
                    rent_status TEXT DEFAULT 'current',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Synced tickets - prevent duplicate forwarding
            conn.execute("""
                CREATE TABLE IF NOT EXISTS synced_tickets (
                    innago_ticket_id TEXT PRIMARY KEY,
                    uisp_ticket_id TEXT,
                    ticket_type TEXT,
                    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Event log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Billing history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS billing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month INTEGER,
                    year INTEGER,
                    occupied_units INTEGER,
                    total_amount REAL,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    # -------------------------------------------------------------------------
    # Unit Tracking
    # -------------------------------------------------------------------------

    def is_unit_tracked(self, unit_number: str) -> bool:
        """Check if unit exists in database."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT 1 FROM units WHERE unit_number = ?",
                (unit_number,)
            )
            return cur.fetchone() is not None

    def is_lease_active(self, lease_id: str) -> bool:
        """Check if a specific lease is currently active."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT 1 FROM units WHERE lease_id = ? AND status = 'active'",
                (lease_id,)
            )
            return cur.fetchone() is not None

    def save_unit(self, unit_number: str, lease_id: str, property_address: str = None,
                  status: str = "active"):
        """Save or update unit record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO units (unit_number, lease_id, property_address, status, rent_status, updated_at)
                VALUES (?, ?, ?, ?, 'current', ?)
                ON CONFLICT(unit_number) DO UPDATE SET
                    lease_id = excluded.lease_id,
                    property_address = excluded.property_address,
                    status = excluded.status,
                    rent_status = 'current',
                    updated_at = excluded.updated_at
            """, (unit_number, lease_id, property_address, status, datetime.now()))
            conn.commit()

    def get_unit(self, unit_number: str) -> dict | None:
        """Get unit record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM units WHERE unit_number = ?",
                (unit_number,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def update_unit_status(self, unit_number: str, status: str):
        """Update unit status (active, suspended, vacant)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE units SET status = ?, updated_at = ? WHERE unit_number = ?",
                (status, datetime.now(), unit_number)
            )
            conn.commit()

    def update_rent_status(self, unit_number: str, rent_status: str):
        """Update rent status (current, delinquent)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE units SET rent_status = ?, updated_at = ? WHERE unit_number = ?",
                (rent_status, datetime.now(), unit_number)
            )
            conn.commit()

    def get_active_units(self) -> list:
        """Get all active (occupied) units."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM units WHERE status = 'active'"
            )
            return [dict(row) for row in cur.fetchall()]

    def get_all_tracked_units(self) -> list:
        """Get all tracked units."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM units")
            return [dict(row) for row in cur.fetchall()]

    def get_delinquent_units(self) -> list:
        """Get units with delinquent rent."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM units WHERE rent_status = 'delinquent'"
            )
            return [dict(row) for row in cur.fetchall()]

    # -------------------------------------------------------------------------
    # Ticket Tracking
    # -------------------------------------------------------------------------

    def is_ticket_synced(self, ticket_id: str) -> bool:
        """Check if ticket has been forwarded."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT 1 FROM synced_tickets WHERE innago_ticket_id = ?",
                (ticket_id,)
            )
            return cur.fetchone() is not None

    def save_synced_ticket(self, innago_ticket_id: str, uisp_ticket_id: str, ticket_type: str):
        """Save synced ticket record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO synced_tickets
                (innago_ticket_id, uisp_ticket_id, ticket_type)
                VALUES (?, ?, ?)
            """, (innago_ticket_id, uisp_ticket_id, ticket_type))
            conn.commit()

    # -------------------------------------------------------------------------
    # Billing History
    # -------------------------------------------------------------------------

    def save_billing_record(self, month: int, year: int, occupied_units: int, total_amount: float):
        """Save billing record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO billing_history (month, year, occupied_units, total_amount)
                VALUES (?, ?, ?, ?)
            """, (month, year, occupied_units, total_amount))
            conn.commit()

    def get_billing_history(self, limit: int = 12) -> list:
        """Get recent billing history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM billing_history ORDER BY year DESC, month DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cur.fetchall()]

    # -------------------------------------------------------------------------
    # Event Logging
    # -------------------------------------------------------------------------

    def log_event(self, event_type: str, details: str):
        """Log an event."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO sync_log (event_type, details) VALUES (?, ?)",
                (event_type, details)
            )
            conn.commit()

    def get_recent_events(self, limit: int = 50) -> list:
        """Get recent events."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM sync_log ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cur.fetchall()]
