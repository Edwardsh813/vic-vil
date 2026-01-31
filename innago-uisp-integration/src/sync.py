"""
Victorian Village - Innago/UISP Integration (Simplified)

Billing model:
- ERE bills apartment complex monthly based on occupied units
- Internet is included in rent (not billed to tenants separately)
- Complex pays: (occupied_units * $45) + upgrade_fees

This integration:
1. Activates ONU when lease starts in Innago
2. Suspends ONU when lease ends
3. Suspends ONU if rent not paid by 5th of month
4. Forwards internet-related maintenance tickets to UISP
5. Generates monthly billing report for the complex
"""

import logging
import re
from datetime import datetime

from .config import Config
from .db import Database
from .innago import InnagoClient
from .uisp import UispNmsClient
from .onu import ONUProvisioner

logger = logging.getLogger(__name__)


class SyncEngine:
    """Simplified sync engine - ONU control + ticket forwarding."""

    def __init__(self, config: Config):
        self.config = config
        self.db = Database()
        self.innago = InnagoClient(config.innago_api_url, config.innago_api_key)
        self.uisp_nms = UispNmsClient(config.uisp_host, config.uisp_nms_api_key)
        self.onu = ONUProvisioner(self.uisp_nms, config.uisp_parent_site_id)

    def run_sync(self):
        """Run a full sync cycle."""
        logger.info("Starting sync cycle")
        try:
            self.sync_leases()
            self.check_rent_delinquency()
            self.sync_maintenance_tickets()
            logger.info("Sync cycle complete")
        except Exception as e:
            logger.error(f"Sync cycle failed: {e}")
            self.db.log_event("sync_error", str(e))

    # -------------------------------------------------------------------------
    # Lease Sync - Activate/Suspend ONUs based on occupancy
    # -------------------------------------------------------------------------

    def sync_leases(self):
        """Sync lease status -> ONU status."""
        logger.info("Syncing leases...")

        # Get all active leases from Innago
        active_leases = self.innago.get_leases(
            self.config.innago_property_id,
            status="active"
        )
        active_units = set()

        for lease in active_leases:
            unit = self._extract_unit_number(lease)
            if not unit:
                continue

            active_units.add(unit)
            lease_id = str(lease.get("id"))

            # Check if we've seen this lease
            if not self.db.is_unit_tracked(unit):
                # New lease - activate ONU
                logger.info(f"New lease detected: unit {unit}")
                self._activate_unit(unit, lease_id, lease)

            elif not self.db.is_lease_active(lease_id):
                # Lease changed (new tenant in same unit)
                logger.info(f"New tenant in unit {unit}")
                self._activate_unit(unit, lease_id, lease)

        # Check for ended leases (units no longer in active list)
        tracked_units = self.db.get_all_tracked_units()
        for unit_record in tracked_units:
            unit = unit_record["unit_number"]
            if unit not in active_units and unit_record["status"] == "active":
                logger.info(f"Lease ended: unit {unit}")
                self._suspend_unit(unit, "Lease ended")

    def _activate_unit(self, unit: str, lease_id: str, lease: dict):
        """Activate ONU for a unit."""
        property_addr = self._extract_property_address(lease)

        # Activate the ONU
        if property_addr:
            self.onu.activate_onu(property_addr, unit)

        # Track in database
        self.db.save_unit(
            unit_number=unit,
            lease_id=lease_id,
            property_address=property_addr,
            status="active"
        )
        self.db.log_event("unit_activated", f"Unit {unit}")

    def _suspend_unit(self, unit: str, reason: str):
        """Suspend ONU for a unit."""
        unit_record = self.db.get_unit(unit)
        if not unit_record:
            return

        property_addr = unit_record.get("property_address")
        if property_addr:
            self.onu.suspend_onu(property_addr, unit, reason)

        self.db.update_unit_status(unit, "suspended")
        self.db.log_event("unit_suspended", f"Unit {unit}: {reason}")

    # -------------------------------------------------------------------------
    # Rent Delinquency - Suspend if not paid by 5th
    # -------------------------------------------------------------------------

    def check_rent_delinquency(self):
        """Check rent payment status and suspend delinquent units."""
        today = datetime.now()

        # Only check after the 5th of the month
        if today.day < 5:
            logger.info("Before grace period (5th) - skipping delinquency check")
            return

        logger.info("Checking rent delinquency...")

        for unit_record in self.db.get_active_units():
            unit = unit_record["unit_number"]
            lease_id = unit_record["lease_id"]

            try:
                # Check if rent is paid in Innago
                balance = self.innago.get_lease_balance(lease_id)

                if balance > 0:
                    # Owes rent - suspend if not already suspended for delinquency
                    if unit_record.get("rent_status") != "delinquent":
                        logger.info(f"Unit {unit} delinquent (balance: ${balance})")
                        self._suspend_for_delinquency(unit, balance)
                else:
                    # Paid up - reactivate if was suspended for delinquency
                    if unit_record.get("rent_status") == "delinquent":
                        logger.info(f"Unit {unit} paid up - reactivating")
                        self._reactivate_after_payment(unit)

            except Exception as e:
                logger.error(f"Error checking balance for unit {unit}: {e}")

    def _suspend_for_delinquency(self, unit: str, balance: float):
        """Suspend ONU for rent delinquency."""
        unit_record = self.db.get_unit(unit)
        if not unit_record:
            return

        property_addr = unit_record.get("property_address")
        if property_addr:
            self.onu.suspend_onu(property_addr, unit, f"Rent delinquent: ${balance}")

        self.db.update_rent_status(unit, "delinquent")
        self.db.log_event("delinquency_suspend", f"Unit {unit}: ${balance} owed")

    def _reactivate_after_payment(self, unit: str):
        """Reactivate ONU after rent payment."""
        unit_record = self.db.get_unit(unit)
        if not unit_record:
            return

        property_addr = unit_record.get("property_address")
        if property_addr:
            self.onu.activate_onu(property_addr, unit)

        self.db.update_rent_status(unit, "current")
        self.db.log_event("delinquency_cleared", f"Unit {unit} paid - reactivated")

    # -------------------------------------------------------------------------
    # Maintenance Tickets - Forward internet issues to UISP
    # -------------------------------------------------------------------------

    def sync_maintenance_tickets(self):
        """Forward internet-related tickets to UISP."""
        logger.info("Checking maintenance tickets...")

        tickets = self.innago.get_maintenance_tickets(
            property_id=self.config.innago_property_id,
            status="open"
        )

        for ticket in tickets:
            ticket_id = str(ticket.get("id"))

            # Skip if already synced
            if self.db.is_ticket_synced(ticket_id):
                continue

            # Check if internet-related
            subject = ticket.get("subject", "").lower()
            description = ticket.get("description", "").lower()
            text = f"{subject} {description}"

            if self._is_internet_related(text):
                self._forward_ticket_to_uisp(ticket)

    def _is_internet_related(self, text: str) -> bool:
        """Check if ticket text contains internet-related keywords."""
        keywords = self.config.internet_keywords
        return any(kw.lower() in text.lower() for kw in keywords)

    def _forward_ticket_to_uisp(self, ticket: dict):
        """Create a ticket in UISP for an internet issue."""
        ticket_id = str(ticket.get("id"))
        unit = self._extract_unit_from_ticket(ticket)

        subject = ticket.get("subject", "Internet Issue")
        description = ticket.get("description", "No description")

        # Build UISP ticket message
        message = f"""Forwarded from Innago (Ticket #{ticket_id})

Unit: {unit or 'Unknown'}
Subject: {subject}

Description:
{description}

---
Reply in UISP or contact tenant directly.
"""

        try:
            # Create ticket in UISP (using jobs/tickets endpoint)
            # Note: UISP NMS doesn't have a direct ticket API like CRM
            # We'll create a job or log it for now
            logger.info(f"Forwarding ticket {ticket_id} to UISP: {subject}")

            # For now, just log - actual UISP ticket creation depends on their setup
            self.db.save_synced_ticket(ticket_id, "forwarded", "internet_support")
            self.db.log_event("ticket_forwarded", f"Innago #{ticket_id}: {subject}")

            # TODO: If using UISP CRM, create actual ticket there
            # self.uisp_crm.create_ticket(client_id, subject, message)

        except Exception as e:
            logger.error(f"Failed to forward ticket {ticket_id}: {e}")

    # -------------------------------------------------------------------------
    # Billing Report - Generate monthly invoice for complex
    # -------------------------------------------------------------------------

    def generate_billing_report(self, month: int = None, year: int = None) -> dict:
        """
        Generate monthly billing report for the apartment complex.

        Returns dict with:
        - occupied_units: count of active units
        - base_rate: per-unit rate
        - base_total: occupied_units * base_rate
        - units_list: list of unit numbers
        """
        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year

        active_units = self.db.get_active_units()
        occupied_count = len(active_units)
        base_rate = self.config.base_rate  # e.g., 45

        report = {
            "month": month,
            "year": year,
            "property": "Victorian Village",
            "occupied_units": occupied_count,
            "total_units": 118,
            "vacancy_count": 118 - occupied_count,
            "base_rate": base_rate,
            "base_total": occupied_count * base_rate,
            "units": [u["unit_number"] for u in active_units],
            "generated_at": datetime.now().isoformat()
        }

        self.db.log_event("billing_report", f"{month}/{year}: {occupied_count} units, ${report['base_total']}")

        return report

    def print_billing_report(self):
        """Print formatted billing report."""
        report = self.generate_billing_report()

        print(f"""
ERE Fiber - Victorian Village - {report['month']}/{report['year']}
{'=' * 50}
Occupied Units:    {report['occupied_units']} / {report['total_units']}
Vacant Units:      {report['vacancy_count']}

Base Rate:         ${report['base_rate']:.2f}/unit
{'=' * 50}
TOTAL DUE:         ${report['base_total']:.2f}
{'=' * 50}

Generated: {report['generated_at']}
""")
        return report

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _extract_unit_number(self, lease: dict) -> str | None:
        """Extract unit number from lease data."""
        unit = lease.get("unitNumber") or lease.get("unit", {}).get("number")
        if unit:
            return str(unit)

        unit_name = lease.get("unit", {}).get("name", "")
        match = re.search(r"(\d+)", unit_name)
        if match:
            return match.group(1)

        return None

    def _extract_property_address(self, lease: dict) -> str | None:
        """Extract property address from lease data."""
        property_info = lease.get("property", {})
        address = property_info.get("address") or property_info.get("name")
        if address:
            return address

        unit_info = lease.get("unit", {})
        property_info = unit_info.get("property", {})
        return property_info.get("address") or property_info.get("name")

    def _extract_unit_from_ticket(self, ticket: dict) -> str | None:
        """Extract unit number from maintenance ticket."""
        unit = ticket.get("unitNumber") or ticket.get("unit", {}).get("number")
        if unit:
            return str(unit)

        text = f"{ticket.get('subject', '')} {ticket.get('description', '')}"
        match = re.search(r"unit\s*#?\s*(\d+)", text, re.IGNORECASE)
        if match:
            return match.group(1)

        return None
