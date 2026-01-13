import sqlite3
from datetime import datetime, date
from typing import Optional
from contextlib import contextmanager
from cryptography.fernet import Fernet
import config

def get_cipher():
    """Get encryption cipher for passwords."""
    if not config.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY not set in environment")
    return Fernet(config.ENCRYPTION_KEY.encode())

def encrypt_password(password: str) -> str:
    """Encrypt a password for storage."""
    cipher = get_cipher()
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted: str) -> str:
    """Decrypt a stored password."""
    cipher = get_cipher()
    return cipher.decrypt(encrypted.encode()).decode()

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    """Initialize the database schema."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Accounts table - stores login credentials for each meter
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_encrypted TEXT NOT NULL,
                meter_id TEXT,
                account_number TEXT,
                address TEXT,
                building_name TEXT,
                unit_number TEXT,
                is_active INTEGER DEFAULT 1,
                last_scraped TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Hourly readings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hourly_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                reading_date DATE NOT NULL,
                hour INTEGER NOT NULL,
                usage_gallons REAL,
                cumulative_reading REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                UNIQUE(account_id, reading_date, hour)
            )
        ''')

        # Daily summaries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                reading_date DATE NOT NULL,
                total_usage_gallons REAL,
                peak_hour INTEGER,
                peak_usage_gallons REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                UNIQUE(account_id, reading_date)
            )
        ''')

        # Alerts configuration table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                alert_type TEXT NOT NULL,
                threshold_value REAL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        ''')

        # Alert history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_config_id INTEGER NOT NULL,
                account_id INTEGER,
                message TEXT NOT NULL,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged INTEGER DEFAULT 0,
                FOREIGN KEY (alert_config_id) REFERENCES alert_configs(id),
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        ''')

        # Scrape logs for debugging
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scrape_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                status TEXT NOT NULL,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        ''')

        conn.commit()

        # Add avg_12mo column if it doesn't exist (migration)
        try:
            cursor.execute('ALTER TABLE accounts ADD COLUMN avg_12mo REAL')
            conn.commit()
        except:
            pass  # Column already exists

        # Add monthly_usage column if it doesn't exist (migration)
        try:
            cursor.execute('ALTER TABLE accounts ADD COLUMN monthly_usage REAL')
            conn.commit()
        except:
            pass  # Column already exists

        print("Database initialized successfully")

# Account management functions
def add_account(email: str, password: str, building_name: str = "", unit_number: str = "",
                account_number: str = "", address: str = "") -> int:
    """Add a new account."""
    encrypted_pw = encrypt_password(password)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO accounts (email, password_encrypted, building_name, unit_number, account_number, address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (email, encrypted_pw, building_name, unit_number, account_number, address))
        return cursor.lastrowid

def get_account(account_id: int) -> Optional[dict]:
    """Get account by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM accounts WHERE id = ?', (account_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None

def get_all_accounts() -> list:
    """Get all active accounts."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM accounts WHERE is_active = 1 ORDER BY building_name, unit_number')
        return [dict(row) for row in cursor.fetchall()]

def update_account(account_id: int, **kwargs):
    """Update account fields."""
    allowed_fields = ['email', 'building_name', 'unit_number', 'meter_id', 'account_number', 'address', 'is_active', 'last_scraped', 'avg_12mo', 'monthly_usage', 'leak_alerts', 'min_overage_pct']
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

    if 'password' in kwargs:
        updates['password_encrypted'] = encrypt_password(kwargs['password'])

    if not updates:
        return

    set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
    values = list(updates.values()) + [account_id]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f'UPDATE accounts SET {set_clause} WHERE id = ?', values)

def delete_account(account_id: int):
    """Soft delete an account."""
    update_account(account_id, is_active=0)

# Reading functions
def save_hourly_reading(account_id: int, reading_date: date, hour: int,
                        usage_gallons: float, cumulative_reading: float = None):
    """Save an hourly reading."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO hourly_readings
            (account_id, reading_date, hour, usage_gallons, cumulative_reading)
            VALUES (?, ?, ?, ?, ?)
        ''', (account_id, reading_date, hour, usage_gallons, cumulative_reading))

def save_daily_summary(account_id: int, reading_date: date, total_usage: float,
                       peak_hour: int = None, peak_usage: float = None):
    """Save a daily summary."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO daily_summaries
            (account_id, reading_date, total_usage_gallons, peak_hour, peak_usage_gallons)
            VALUES (?, ?, ?, ?, ?)
        ''', (account_id, reading_date, total_usage, peak_hour, peak_usage))

def get_hourly_readings(account_id: int, reading_date: date) -> list:
    """Get hourly readings for a specific date."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM hourly_readings
            WHERE account_id = ? AND reading_date = ?
            ORDER BY hour
        ''', (account_id, reading_date))
        return [dict(row) for row in cursor.fetchall()]

def get_daily_summaries(account_id: int, start_date: date = None, end_date: date = None) -> list:
    """Get daily summaries for an account."""
    with get_db() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM daily_summaries WHERE account_id = ?'
        params = [account_id]

        if start_date:
            query += ' AND reading_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND reading_date <= ?'
            params.append(end_date)

        query += ' ORDER BY reading_date DESC'
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_all_daily_summaries(reading_date: date) -> list:
    """Get all daily summaries for a specific date."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ds.*, a.building_name, a.unit_number, a.email
            FROM daily_summaries ds
            JOIN accounts a ON ds.account_id = a.id
            WHERE ds.reading_date = ?
            ORDER BY a.building_name, a.unit_number
        ''', (reading_date,))
        return [dict(row) for row in cursor.fetchall()]

# Alert functions
def add_alert_config(alert_type: str, threshold_value: float, account_id: int = None) -> int:
    """Add an alert configuration."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alert_configs (account_id, alert_type, threshold_value)
            VALUES (?, ?, ?)
        ''', (account_id, alert_type, threshold_value))
        return cursor.lastrowid

def get_alert_configs(account_id: int = None) -> list:
    """Get alert configurations."""
    with get_db() as conn:
        cursor = conn.cursor()
        if account_id:
            cursor.execute('''
                SELECT * FROM alert_configs
                WHERE (account_id = ? OR account_id IS NULL) AND is_active = 1
            ''', (account_id,))
        else:
            cursor.execute('SELECT * FROM alert_configs WHERE is_active = 1')
        return [dict(row) for row in cursor.fetchall()]

def save_alert(alert_config_id: int, account_id: int, message: str):
    """Save a triggered alert."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alert_history (alert_config_id, account_id, message)
            VALUES (?, ?, ?)
        ''', (alert_config_id, account_id, message))

def get_recent_alerts(limit: int = 50) -> list:
    """Get recent alerts."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ah.*, a.building_name, a.unit_number, ac.alert_type
            FROM alert_history ah
            LEFT JOIN accounts a ON ah.account_id = a.id
            JOIN alert_configs ac ON ah.alert_config_id = ac.id
            ORDER BY ah.triggered_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

# Logging functions
def log_scrape(account_id: int, status: str, message: str = ""):
    """Log a scrape attempt."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scrape_logs (account_id, status, message)
            VALUES (?, ?, ?)
        ''', (account_id, status, message))

if __name__ == "__main__":
    init_db()
