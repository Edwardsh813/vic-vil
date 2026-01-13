import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "water_monitor.db")

# Scraping settings
SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", "1"))
BASE_URL = "https://mywateradvisor2.com/"

# Alert settings
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_FROM_EMAIL = os.getenv("ALERT_FROM_EMAIL", "")
ALERT_TO_EMAIL = os.getenv("ALERT_TO_EMAIL", "")

# Encryption key for storing passwords
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# Flask
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
