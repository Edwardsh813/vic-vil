"""
Notification system for Water Monitor using ntfy.sh
"""

import requests

NTFY_TOPIC = "https://ntfy.sh/vicvill-water"


def send_notification(title: str, message: str, priority: str = "default", tags: list = None):
    """Send a notification via ntfy.sh"""
    try:
        headers = {
            "Title": title,
            "Priority": priority,
        }
        if tags:
            headers["Tags"] = ",".join(tags)

        response = requests.post(
            NTFY_TOPIC,
            data=message,
            headers=headers,
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send notification: {e}")
        return False


def send_leak_alert(address: str, message: str):
    """Send a leak detection alert."""
    return send_notification(
        title=f"LEAK: {address}",
        message=message,
        priority="urgent",
        tags=["droplet", "warning"]
    )


def send_overage_alert(address: str, message: str):
    """Send an overage projection alert."""
    return send_notification(
        title=f"Overage Alert: {address}",
        message=message,
        priority="high",
        tags=["chart_increasing", "warning"]
    )
