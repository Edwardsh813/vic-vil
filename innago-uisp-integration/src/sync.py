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
from .uisp import UispNmsClient, UispCrmClient
from .onu import ONUProvisioner, find_onu_by_unit

logger = logging.getLogger(__name__)


class SyncEngine:
    """Simplified sync engine - ONU control + ticket forwarding."""

    def __init__(self, config: Config):
        self.config = config
        self.db = Database()
        self.innago = InnagoClient(config.innago_api_url, config.innago_api_key)
        self.uisp_nms = UispNmsClient(config.uisp_host, config.uisp_nms_api_key)
        self.uisp_crm = UispCrmClient(config.uisp_host, config.uisp_crm_api_key)
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
        """Activate ONU for a unit with default package speeds."""
        property_addr = self._extract_property_address(lease)

        # Get tenant ID for notifications
        tenant_id = None
        try:
            tenants = self.innago.get_tenants_by_lease(lease_id)
            if tenants:
                tenant_id = str(tenants[0].get("id"))
        except Exception:
            pass

        # Get default package speeds
        default_pkg = self.config.default_package
        download = default_pkg.get("download", 500)
        upload = default_pkg.get("upload", 500)

        # Activate the ONU with bandwidth limits
        if property_addr:
            self.onu.activate_onu(property_addr, unit, download, upload)

        # Track in database
        self.db.save_unit(
            unit_number=unit,
            lease_id=lease_id,
            tenant_id=tenant_id,
            property_address=property_addr,
            status="active",
            package=default_pkg.get("name", "VIC-VIL 500")
        )
        self.db.log_event("unit_activated", f"Unit {unit} @ {download}/{upload} Mbps")

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
        """Suspend ONU for rent delinquency and notify tenant."""
        unit_record = self.db.get_unit(unit)
        if not unit_record:
            return

        property_addr = unit_record.get("property_address")
        if property_addr:
            self.onu.suspend_onu(property_addr, unit, f"Rent delinquent: ${balance}")

        # Notify tenant through Innago
        tenant_id = unit_record.get("tenant_id")
        if tenant_id:
            try:
                self.innago.notify_internet_suspended(tenant_id, "unpaid rent")
                logger.info(f"Sent suspension notice to tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Failed to send suspension notice: {e}")

        self.db.update_rent_status(unit, "delinquent")
        self.db.log_event("delinquency_suspend", f"Unit {unit}: ${balance} owed")

    def _reactivate_after_payment(self, unit: str):
        """Reactivate ONU after rent payment and notify tenant."""
        unit_record = self.db.get_unit(unit)
        if not unit_record:
            return

        property_addr = unit_record.get("property_address")
        if property_addr:
            self.onu.activate_onu(property_addr, unit)

        # Notify tenant through Innago
        tenant_id = unit_record.get("tenant_id")
        if tenant_id:
            try:
                self.innago.notify_internet_restored(tenant_id)
                logger.info(f"Sent restoration notice to tenant {tenant_id}")
            except Exception as e:
                logger.warning(f"Failed to send restoration notice: {e}")

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

            # Check for upgrade request first (hidden feature)
            if self._is_upgrade_request(text):
                self._handle_upgrade_request(ticket)
            elif self._is_internet_related(text):
                self._forward_ticket_to_uisp(ticket)

    def _is_internet_related(self, text: str) -> bool:
        """Check if ticket text contains internet-related keywords."""
        keywords = self.config.internet_keywords
        return any(kw.lower() in text.lower() for kw in keywords)

    def _is_upgrade_request(self, text: str) -> bool:
        """Check if ticket is requesting a speed upgrade."""
        upgrade_keywords = ["upgrade", "faster", "1g", "2g", "gigabit", "speed upgrade"]
        return any(kw in text.lower() for kw in upgrade_keywords)

    def _handle_upgrade_request(self, ticket: dict):
        """
        Handle a package upgrade request (hidden feature).
        Upgrades are available but not advertised.
        """
        ticket_id = str(ticket.get("id"))
        unit = self._extract_unit_from_ticket(ticket)

        if not unit:
            logger.warning(f"Could not determine unit for upgrade ticket {ticket_id}")
            return

        text = f"{ticket.get('subject', '')} {ticket.get('description', '')}".lower()

        # Determine requested package
        new_package_name = None
        if "2g" in text or "2000" in text or "2 gig" in text:
            new_package_name = "VIC-VIL 2G"
        elif "1g" in text or "1000" in text or "gigabit" in text or "1 gig" in text:
            new_package_name = "VIC-VIL 1G"
        else:
            # Can't determine package, forward as regular ticket
            self._forward_ticket_to_uisp(ticket)
            return

        new_package = self.config.get_package_by_name(new_package_name)
        if not new_package:
            logger.warning(f"Package {new_package_name} not found in config")
            return

        unit_record = self.db.get_unit(unit)
        if not unit_record:
            logger.warning(f"No unit record for {unit}")
            return

        try:
            # Apply new speed to ONU
            property_addr = unit_record.get("property_address")
            if property_addr:
                download = new_package.get("download", 500)
                upload = new_package.get("upload", 500)
                self.onu.set_onu_speed(property_addr, unit, download, upload)

            # Update package in database
            self.db.update_unit_package(unit, new_package_name)

            # Log the upgrade
            addon_price = new_package.get("addon", 0)
            self.db.save_synced_ticket(ticket_id, "", "upgrade")
            self.db.log_event("upgrade_processed", f"Unit {unit} -> {new_package_name} (+${addon_price}/mo)")

            logger.info(f"Upgraded unit {unit} to {new_package_name} ({download}/{upload} Mbps)")

        except Exception as e:
            logger.error(f"Failed to process upgrade for unit {unit}: {e}")

    def _forward_ticket_to_uisp(self, ticket: dict):
        """Create a ticket in UISP CRM linked to the tenant's ONU."""
        ticket_id = str(ticket.get("id"))
        unit = self._extract_unit_from_ticket(ticket)

        subject = ticket.get("subject", "Internet Issue")
        description = ticket.get("description", "No description")

        # Get ONU info for this unit
        onu_info = None
        onu_name = "Unknown"
        onu_id = None

        if unit:
            unit_record = self.db.get_unit(unit)
            property_addr = unit_record.get("property_address") if unit_record else None

            if property_addr:
                onu_info = find_onu_by_unit(property_addr, unit)
                if onu_info:
                    onu_name = onu_info.get("onu_name", f"Unit {unit}")
                    onu_id = onu_info.get("uisp_id")

        # Build ticket message with ONU details
        message = f"""Forwarded from Innago (Ticket #{ticket_id})

Unit: {unit or 'Unknown'}
ONU: {onu_name}
ONU Device ID: {onu_id or 'Not found'}

Tenant Issue:
{description}

---
View ONU in UISP NMS: http://{self.config.uisp_host}/nms/#/devices/{onu_id}/overview
"""

        try:
            # Create ticket in UISP CRM
            # Use the Victorian Village master client or create ticket without client
            uisp_ticket = self.uisp_crm.create_ticket_for_device(
                subject=f"[Unit {unit}] {subject}",
                message=message,
                device_id=onu_id
            )
            uisp_ticket_id = str(uisp_ticket.get("id", ""))

            logger.info(f"Created UISP ticket {uisp_ticket_id} for Innago #{ticket_id}")

            self.db.save_synced_ticket(ticket_id, uisp_ticket_id, "internet_support")
            self.db.log_event("ticket_forwarded", f"Innago #{ticket_id} -> UISP #{uisp_ticket_id} (ONU: {onu_name})")

            # TODO: If using UISP CRM, create actual ticket there
            # self.uisp_crm.create_ticket(client_id, subject, message)

        except Exception as e:
            logger.error(f"Failed to forward ticket {ticket_id}: {e}")

    # -------------------------------------------------------------------------
    # Billing Report - Generate monthly invoice for complex
    # -------------------------------------------------------------------------

    def generate_billing_report(self, month: int = None, year: int = None,
                                 create_invoice: bool = False) -> dict:
        """
        Generate monthly billing report for the apartment complex.

        Args:
            month: Billing month
            year: Billing year
            create_invoice: If True, create invoice in UISP for the complex

        Returns dict with billing details.
        """
        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year

        active_units = self.db.get_active_units()
        occupied_count = len(active_units)
        base_rate = self.config.base_rate

        # Count upgrades
        upgrades = {"VIC-VIL 1G": 0, "VIC-VIL 2G": 0}
        for unit in active_units:
            pkg = unit.get("package", "VIC-VIL 500")
            if pkg in upgrades:
                upgrades[pkg] += 1

        upgrade_total = (upgrades["VIC-VIL 1G"] * 10) + (upgrades["VIC-VIL 2G"] * 20)
        base_total = occupied_count * base_rate

        report = {
            "month": month,
            "year": year,
            "property": "Victorian Village",
            "occupied_units": occupied_count,
            "total_units": self.config.total_units,
            "vacancy_count": self.config.total_units - occupied_count,
            "base_rate": base_rate,
            "base_total": base_total,
            "upgrades_1g": upgrades["VIC-VIL 1G"],
            "upgrades_2g": upgrades["VIC-VIL 2G"],
            "upgrade_total": upgrade_total,
            "grand_total": base_total + upgrade_total,
            "units": [u["unit_number"] for u in active_units],
            "generated_at": datetime.now().isoformat()
        }

        # Create invoice in UISP if requested
        if create_invoice:
            try:
                client = self.uisp_crm.get_or_create_billing_client(
                    company_name="Victorian Village Apartments",
                    email=self.config.complex_billing_email
                )
                invoice = self.uisp_crm.create_monthly_invoice(
                    client_id=int(client["id"]),
                    occupied_units=occupied_count,
                    base_rate=base_rate,
                    upgrades=upgrades
                )
                report["uisp_invoice_id"] = invoice.get("id")
                logger.info(f"Created UISP invoice {invoice.get('id')} for ${report['grand_total']}")
            except Exception as e:
                logger.error(f"Failed to create UISP invoice: {e}")

        self.db.log_event("billing_report", f"{month}/{year}: {occupied_count} units, ${report['grand_total']}")

        return report

    def print_billing_report(self, create_invoice: bool = False):
        """Print formatted billing report."""
        report = self.generate_billing_report(create_invoice=create_invoice)

        print(f"""
ERE Fiber - Victorian Village - {report['month']}/{report['year']}
{'=' * 50}
Occupied Units:    {report['occupied_units']} / {report['total_units']}
Vacant Units:      {report['vacancy_count']}

Base Service ({report['occupied_units']} × ${report['base_rate']:.2f}):  ${report['base_total']:.2f}
""")

        if report['upgrades_1g'] > 0 or report['upgrades_2g'] > 0:
            print(f"Upgrades:")
            if report['upgrades_1g'] > 0:
                print(f"  1G Upgrade ({report['upgrades_1g']} × $10):       ${report['upgrades_1g'] * 10:.2f}")
            if report['upgrades_2g'] > 0:
                print(f"  2G Upgrade ({report['upgrades_2g']} × $20):       ${report['upgrades_2g'] * 20:.2f}")

        print(f"""{'=' * 50}
TOTAL DUE:         ${report['grand_total']:.2f}
{'=' * 50}
""")

        if report.get("uisp_invoice_id"):
            print(f"UISP Invoice Created: #{report['uisp_invoice_id']}")

        print(f"Generated: {report['generated_at']}")
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
