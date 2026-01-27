import sqlite3
from pathlib import Path
from datetime import datetime


class Database:
    def __init__(self, db_path: str = "sync_state.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS synced_leases (
                    innago_lease_id TEXT PRIMARY KEY,
                    innago_tenant_id TEXT,
                    uisp_client_id TEXT,
                    uisp_service_id TEXT,
                    unit_number TEXT,
                    property_address TEXT,
                    innago_charge_id TEXT,
                    current_package TEXT,
                    status TEXT DEFAULT 'active',
                    service_status TEXT DEFAULT 'active',
                    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS synced_tickets (
                    innago_ticket_id TEXT PRIMARY KEY,
                    uisp_ticket_id TEXT,
                    ticket_type TEXT,
                    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def is_lease_synced(self, lease_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT 1 FROM synced_leases WHERE innago_lease_id = ?",
                (lease_id,)
            )
            return cur.fetchone() is not None

    def save_synced_lease(self, lease_id: str, tenant_id: str, uisp_client_id: str,
                          uisp_service_id: str, unit_number: str,
                          property_address: str = None, innago_charge_id: str = None,
                          current_package: str = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO synced_leases
                (innago_lease_id, innago_tenant_id, uisp_client_id, uisp_service_id,
                 unit_number, property_address, innago_charge_id, current_package, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """, (lease_id, tenant_id, uisp_client_id, uisp_service_id,
                  unit_number, property_address, innago_charge_id, current_package))
            conn.commit()

    def update_lease_package(self, lease_id: str, innago_charge_id: str, package_name: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE synced_leases
                SET innago_charge_id = ?, current_package = ?
                WHERE innago_lease_id = ?
            """, (innago_charge_id, package_name, lease_id))
            conn.commit()

    def get_uisp_client_for_lease(self, lease_id: str) -> dict | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM synced_leases WHERE innago_lease_id = ?",
                (lease_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def is_ticket_synced(self, ticket_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT 1 FROM synced_tickets WHERE innago_ticket_id = ?",
                (ticket_id,)
            )
            return cur.fetchone() is not None

    def save_synced_ticket(self, innago_ticket_id: str, uisp_ticket_id: str, ticket_type: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO synced_tickets
                (innago_ticket_id, uisp_ticket_id, ticket_type)
                VALUES (?, ?, ?)
            """, (innago_ticket_id, uisp_ticket_id, ticket_type))
            conn.commit()

    def log_event(self, event_type: str, details: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO sync_log (event_type, details) VALUES (?, ?)",
                (event_type, details)
            )
            conn.commit()

    def get_synced_lease(self, lease_id: str) -> dict | None:
        """Get synced lease record by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM synced_leases WHERE innago_lease_id = ?",
                (lease_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def update_lease_status(self, lease_id: str, status: str):
        """Update lease status (active, ended, etc.)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE synced_leases SET status = ? WHERE innago_lease_id = ?",
                (status, lease_id)
            )
            conn.commit()

    def get_active_leases(self) -> list:
        """Get all active synced leases."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM synced_leases WHERE status = 'active'"
            )
            return [dict(row) for row in cur.fetchall()]

    def update_service_status(self, lease_id: str, service_status: str):
        """Update service status (active, suspended) - tracks UISP billing status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE synced_leases SET service_status = ? WHERE innago_lease_id = ?",
                (service_status, lease_id)
            )
            conn.commit()
