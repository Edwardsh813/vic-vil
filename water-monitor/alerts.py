"""
Alert System for Water Monitor

Supports various alert types:
- high_daily_usage: Alert when daily usage exceeds threshold
- high_hourly_usage: Alert when hourly usage exceeds threshold
- no_data: Alert when no data received for X hours
- leak_detection: Alert when continuous usage detected (possible leak)
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from typing import Optional
import database as db
import config


# Alert type constants
ALERT_HIGH_DAILY = 'high_daily_usage'
ALERT_HIGH_HOURLY = 'high_hourly_usage'
ALERT_NO_DATA = 'no_data'
ALERT_LEAK = 'leak_detection'


def send_email_alert(subject: str, body: str, to_email: str = None):
    """Send an email alert."""
    if not config.SMTP_USERNAME or not config.SMTP_PASSWORD:
        print(f"Email not configured. Alert: {subject}")
        return False

    to_email = to_email or config.ALERT_TO_EMAIL
    if not to_email:
        print(f"No recipient email configured. Alert: {subject}")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = config.ALERT_FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = f"[Water Monitor] {subject}"

        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.starttls()
        server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def check_high_daily_usage(account_id: int, threshold: float) -> Optional[str]:
    """Check if daily usage exceeds threshold."""
    today = date.today()
    summaries = db.get_daily_summaries(account_id, today, today)

    if summaries and summaries[0]['total_usage_gallons']:
        usage = summaries[0]['total_usage_gallons']
        if usage > threshold:
            return f"High daily usage detected: {usage:.1f} gallons (threshold: {threshold:.1f})"

    return None


def check_high_hourly_usage(account_id: int, threshold: float) -> Optional[str]:
    """Check if any hourly usage exceeds threshold."""
    today = date.today()
    readings = db.get_hourly_readings(account_id, today)

    for reading in readings:
        if reading['usage_gallons'] and reading['usage_gallons'] > threshold:
            return f"High hourly usage at hour {reading['hour']}: {reading['usage_gallons']:.1f} gallons (threshold: {threshold:.1f})"

    return None


def check_no_data(account_id: int, hours_threshold: float) -> Optional[str]:
    """Check if no data has been received for X hours."""
    account = db.get_account(account_id)

    if account and account['last_scraped']:
        last_scraped = datetime.fromisoformat(account['last_scraped'])
        hours_since = (datetime.now() - last_scraped).total_seconds() / 3600

        if hours_since > hours_threshold:
            return f"No data received for {hours_since:.1f} hours (threshold: {hours_threshold:.1f})"

    return None


def check_leak_detection(account_id: int, min_continuous_hours: float) -> Optional[str]:
    """
    Check for potential leaks by detecting continuous water usage.
    A leak is suspected if water is being used every hour for X continuous hours.
    """
    today = date.today()
    readings = db.get_hourly_readings(account_id, today)

    if len(readings) < min_continuous_hours:
        return None

    # Check for continuous usage
    continuous_count = 0
    for reading in readings:
        if reading['usage_gallons'] and reading['usage_gallons'] > 0:
            continuous_count += 1
        else:
            continuous_count = 0

        if continuous_count >= min_continuous_hours:
            return f"Possible leak detected: Continuous water usage for {continuous_count} hours"

    return None


def process_alerts():
    """Process all alert configurations and trigger alerts as needed."""
    accounts = db.get_all_accounts()
    triggered_alerts = []

    for account in accounts:
        account_id = account['id']
        alert_configs = db.get_alert_configs(account_id)

        for config_item in alert_configs:
            alert_type = config_item['alert_type']
            threshold = config_item['threshold_value']
            message = None

            if alert_type == ALERT_HIGH_DAILY:
                message = check_high_daily_usage(account_id, threshold)
            elif alert_type == ALERT_HIGH_HOURLY:
                message = check_high_hourly_usage(account_id, threshold)
            elif alert_type == ALERT_NO_DATA:
                message = check_no_data(account_id, threshold)
            elif alert_type == ALERT_LEAK:
                message = check_leak_detection(account_id, threshold)

            if message:
                # Build full alert message
                full_message = f"""
                <h2>Water Usage Alert</h2>
                <p><strong>Building:</strong> {account['building_name']}</p>
                <p><strong>Unit:</strong> {account['unit_number']}</p>
                <p><strong>Alert Type:</strong> {alert_type}</p>
                <p><strong>Details:</strong> {message}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                """

                # Save alert to database
                db.save_alert(config_item['id'], account_id, message)

                # Send email notification
                subject = f"Alert: {alert_type} - {account['building_name']} Unit {account['unit_number']}"
                send_email_alert(subject, full_message)

                triggered_alerts.append({
                    'account_id': account_id,
                    'building': account['building_name'],
                    'unit': account['unit_number'],
                    'type': alert_type,
                    'message': message
                })

    return triggered_alerts


def send_daily_summary():
    """Send a daily summary email with all meter readings."""
    today = date.today()
    summaries = db.get_all_daily_summaries(today)

    if not summaries:
        return

    # Group by building
    buildings = {}
    total_usage = 0

    for s in summaries:
        building = s['building_name'] or 'Unknown'
        if building not in buildings:
            buildings[building] = []
        buildings[building].append(s)
        if s['total_usage_gallons']:
            total_usage += s['total_usage_gallons']

    # Build email body
    body = f"""
    <h1>Daily Water Usage Summary - {today}</h1>
    <p><strong>Total Usage Across All Meters:</strong> {total_usage:.1f} gallons</p>
    <hr>
    """

    for building, units in sorted(buildings.items()):
        building_total = sum(u['total_usage_gallons'] or 0 for u in units)
        body += f"<h2>{building} (Total: {building_total:.1f} gal)</h2>"
        body += "<table border='1' cellpadding='5'>"
        body += "<tr><th>Unit</th><th>Usage (gal)</th><th>Peak Hour</th></tr>"

        for unit in sorted(units, key=lambda x: x['unit_number'] or ''):
            usage = unit['total_usage_gallons'] or 0
            peak = unit['peak_hour'] or '-'
            body += f"<tr><td>{unit['unit_number']}</td><td>{usage:.1f}</td><td>{peak}</td></tr>"

        body += "</table><br>"

    # Send email
    send_email_alert(f"Daily Summary - {today}", body)


if __name__ == "__main__":
    # Test alerts
    alerts = process_alerts()
    print(f"Triggered {len(alerts)} alerts")

    for alert in alerts:
        print(f"  - {alert['building']} {alert['unit']}: {alert['message']}")
