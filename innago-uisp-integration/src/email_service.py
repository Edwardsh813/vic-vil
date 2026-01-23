import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .config import Config

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for tenant notifications."""

    def __init__(self, config: Config):
        self.config = config

    def _send_email(self, to_email: str, subject: str, body_html: str):
        """Send an email."""
        if not to_email:
            logger.warning("No email address provided, skipping email")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.config.email_from
        msg["To"] = to_email

        msg.attach(MIMEText(body_html, "html"))

        try:
            with smtplib.SMTP(self.config.email_smtp_host, self.config.email_smtp_port) as server:
                server.starttls()
                server.login(self.config.email_smtp_user, self.config.email_smtp_pass)
                server.sendmail(self.config.email_from, to_email, msg.as_string())
            logger.info(f"Email sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")

    def send_welcome_email(self, to_email: str, tenant_name: str, unit_number: str,
                           lease_start: str, package_name: str, speed: int):
        """Send welcome email to new tenant."""

        subject = f"Your Village Fiber Internet is Ready - Unit {unit_number}"

        body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ color: #2c5530; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
        a {{ color: #2c5530; }}
        .highlight {{ background-color: #f0f7f1; padding: 15px; border-radius: 5px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h2 class="header">Welcome to Village Fiber!</h2>

        <p>Hi {tenant_name},</p>

        <p>Welcome to Victorian Village! Your Village Fiber internet is active starting <strong>{lease_start}</strong>.</p>

        <div class="highlight">
            <strong>Important:</strong> A router is not included. You'll need to provide your own WiFi router
            to connect - just plug it into the fiber jack in your unit.
        </div>

        <p><strong>Recommended Router:</strong><br>
        <a href="https://www.amazon.com/TP-Link-WiFi-AX3000-Smart-Router/dp/B09G5W9R6R">TP-Link Archer AX55 - $70</a></p>

        <p><em>Note: If you plan on upgrading to Village Fiber 2G, you'll need the
        <a href="https://www.amazon.com/TP-Link-AX3000-Archer-AX55-Pro/dp/B0BTD7V93F">Pro model</a>
        to get full speeds.</em></p>

        <h3>Your Current Plan</h3>
        <p><strong>{package_name}</strong> ({speed} Mbps) - Included with rent</p>

        <h3>Want Faster Speeds?</h3>
        <p>Submit a maintenance request in your tenant portal with subject "Internet Upgrade" and your choice:</p>

        <table>
            <tr>
                <th>Package</th>
                <th>Speed</th>
                <th>Add-on</th>
            </tr>
            <tr>
                <td>Village Fiber 1G</td>
                <td>1 Gbps</td>
                <td>+$10/mo</td>
            </tr>
            <tr>
                <td>Village Fiber 2G</td>
                <td>2 Gbps</td>
                <td>+$15/mo</td>
            </tr>
        </table>

        <h3>Need Help?</h3>
        <p>Internet issues? Submit a maintenance request with "Internet" in the subject.</p>

        <p>— ERE Fiber LLC</p>
    </div>
</body>
</html>
"""

        self._send_email(to_email, subject, body)
