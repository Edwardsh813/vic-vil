import logging
import re
from datetime import datetime

from .config import Config
from .db import Database
from .innago import InnagoClient
from .uisp import UispCrmClient, UispNmsClient
from .onu import ONUProvisioner, find_onu_by_unit
try:
    from .email_service import EmailService
except ImportError:
    EmailService = None

logger = logging.getLogger(__name__)


class SyncEngine:
    """Main sync engine for Innago <-> UISP integration."""

    def __init__(self, config: Config):
        self.config = config
        self.db = Database()
        self.innago = InnagoClient(config.innago_api_url, config.innago_api_key)
        self.uisp_crm = UispCrmClient(config.uisp_host, config.uisp_crm_api_key)
        self.uisp_nms = UispNmsClient(config.uisp_host, config.uisp_nms_api_key)

        # Email is optional
        self.email = None
        if EmailService and config.email_smtp_host and config.email_smtp_host != "NEED_TO_SET":
            try:
                self.email = EmailService(config)
            except Exception as e:
                logger.warning(f"Email service not configured: {e}")

        # ONU provisioner for activating/suspending ONUs
        self.onu_provisioner = ONUProvisioner(self.uisp_nms, config.uisp_parent_site_id)

    def get_package_by_name(self, name: str) -> dict | None:
        """Get package config by name."""
        for pkg in self.config.packages:
            if pkg["name"].lower() == name.lower():
                return pkg
        return None

    def get_plan_id_for_package(self, package: dict) -> str:
        """Get UISP plan ID from package config."""
        return str(package.get("uisp_plan_id"))

    def run_sync(self):
        """Run a full sync cycle."""
        logger.info("Starting sync cycle")
        try:
            self.sync_new_leases()
            self.sync_ended_leases()
            self.sync_uisp_billing_status()  # Poll UISP for suspensions/reactivations
            self.sync_maintenance_tickets()
            logger.info("Sync cycle complete")
        except Exception as e:
            logger.error(f"Sync cycle failed: {e}")
            self.db.log_event("sync_error", str(e))

    def sync_new_leases(self):
        """Check for new leases and provision service in UISP."""
        logger.info("Checking for new leases...")

        leases = self.innago.get_leases(self.config.innago_property_id)

        for lease in leases:
            lease_id = str(lease.get("id"))

            # Skip if already synced
            if self.db.is_lease_synced(lease_id):
                continue

            # Get lease details
            unit_number = self._extract_unit_number(lease)
            if not unit_number:
                logger.warning(f"Could not extract unit number for lease {lease_id}")
                continue

            # Get property address for ONU mapping
            property_address = self._extract_property_address(lease)

            # Get tenant info
            tenants = self.innago.get_tenants_by_lease(lease_id)
            if not tenants:
                logger.warning(f"No tenants found for lease {lease_id}")
                continue

            tenant = tenants[0]  # Primary tenant
            tenant_id = str(tenant.get("id"))

            logger.info(f"Processing new lease: {lease_id} for unit {unit_number}")

            try:
                # Create client in UISP
                uisp_client = self.uisp_crm.create_client(
                    first_name=tenant.get("firstName", ""),
                    last_name=tenant.get("lastName", ""),
                    email=tenant.get("email", ""),
                    street=f"Unit {unit_number}",
                    note=f"Innago Lease: {lease_id}"
                )
                uisp_client_id = str(uisp_client.get("id"))
                logger.info(f"Created UISP client: {uisp_client_id}")

                # Get default package and service plan
                default_pkg = self.config.default_package
                plan_id = self.get_plan_id_for_package(default_pkg)
                if not plan_id:
                    logger.error(f"No uisp_plan_id configured for: {default_pkg['name']}")
                    continue

                # Create service
                lease_start = lease.get("startDate", datetime.now().strftime("%Y-%m-%d"))
                uisp_service = self.uisp_crm.create_service(
                    client_id=uisp_client_id,
                    service_plan_id=plan_id,
                    active_from=lease_start,
                    note=f"Unit {unit_number}"
                )
                uisp_service_id = str(uisp_service.get("id"))
                logger.info(f"Created UISP service: {uisp_service_id}")

                # Create or find subscriber site
                site = self._get_or_create_site(unit_number)

                # Activate ONU for this unit
                self._assign_onu_to_unit(unit_number, site, property_address)

                # Add recurring charge to Innago
                innago_charge = self.innago.create_recurring_charge(
                    lease_id=lease_id,
                    description=f"Internet - {default_pkg['name']}",
                    amount=default_pkg["base_price"],
                    category="Utilities"
                )
                innago_charge_id = str(innago_charge.get("id", ""))
                logger.info(f"Created Innago recurring charge: {innago_charge_id}")

                # Save sync state
                self.db.save_synced_lease(
                    lease_id=lease_id,
                    tenant_id=tenant_id,
                    uisp_client_id=uisp_client_id,
                    uisp_service_id=uisp_service_id,
                    unit_number=unit_number,
                    property_address=property_address,
                    innago_charge_id=innago_charge_id,
                    current_package=default_pkg["name"]
                )

                # Send welcome email (if configured)
                if self.email:
                    self.email.send_welcome_email(
                        to_email=tenant.get("email", ""),
                        tenant_name=tenant.get("firstName", "Resident"),
                        unit_number=unit_number,
                        lease_start=lease_start,
                        package_name=default_pkg["name"],
                        speed=default_pkg["speed_down"]
                    )

                self.db.log_event("lease_synced", f"Unit {unit_number}, Client {uisp_client_id}")
                logger.info(f"Successfully provisioned unit {unit_number}")

            except Exception as e:
                logger.error(f"Failed to provision lease {lease_id}: {e}")
                self.db.log_event("provision_error", f"Lease {lease_id}: {e}")

    def sync_ended_leases(self):
        """Check for ended leases and suspend service/ONU."""
        logger.info("Checking for ended leases...")

        # Get all leases including ended ones
        leases = self.innago.get_leases(
            self.config.innago_property_id,
            status="ended"  # or "terminated", "expired" depending on Innago API
        )

        for lease in leases:
            lease_id = str(lease.get("id"))

            # Check if we have this lease synced and it's still active
            sync_record = self.db.get_synced_lease(lease_id)
            if not sync_record:
                continue  # Not our lease or already handled

            if sync_record.get("status") == "ended":
                continue  # Already processed

            unit_number = sync_record.get("unit_number")
            property_address = self._extract_property_address(lease)

            logger.info(f"Processing ended lease: {lease_id} for unit {unit_number}")

            try:
                # Suspend service in UISP
                uisp_service_id = sync_record.get("uisp_service_id")
                if uisp_service_id:
                    self.uisp_crm.update_service(uisp_service_id, {"status": 0})  # Inactive
                    logger.info(f"Suspended UISP service: {uisp_service_id}")

                # Suspend ONU
                if property_address and unit_number:
                    self.onu_provisioner.suspend_onu(
                        property_address, unit_number,
                        reason=f"Lease ended: {lease_id}"
                    )

                # Delete recurring charge in Innago
                innago_charge_id = sync_record.get("innago_charge_id")
                if innago_charge_id:
                    self.innago.delete_recurring_charge(innago_charge_id)
                    logger.info(f"Deleted Innago charge: {innago_charge_id}")

                # Update sync record
                self.db.update_lease_status(lease_id, "ended")
                self.db.log_event("lease_ended", f"Unit {unit_number}, Lease {lease_id}")
                logger.info(f"Successfully processed ended lease for unit {unit_number}")

            except Exception as e:
                logger.error(f"Failed to process ended lease {lease_id}: {e}")
                self.db.log_event("lease_end_error", f"Lease {lease_id}: {e}")

    def sync_uisp_billing_status(self):
        """
        Poll UISP for service status changes (suspensions/reactivations).

        When UISP suspends service for non-payment:
          - Suspend the ONU
          - Create prorated credit in Innago

        When UISP reactivates service (payment received):
          - Activate the ONU
        """
        logger.info("Checking UISP billing status...")

        # Get all active synced leases
        active_leases = self.db.get_active_leases()

        for lease_record in active_leases:
            uisp_service_id = lease_record.get("uisp_service_id")
            if not uisp_service_id:
                continue

            try:
                # Get current service status from UISP
                services = self.uisp_crm.get_services(lease_record.get("uisp_client_id"))
                service = next((s for s in services if str(s.get("id")) == uisp_service_id), None)

                if not service:
                    continue

                uisp_status = service.get("status")  # 1=active, 2=suspended, etc.
                current_status = lease_record.get("service_status", "active")
                unit_number = lease_record.get("unit_number")
                property_address = lease_record.get("property_address")

                # UISP suspended service (non-payment)
                if uisp_status == 2 and current_status != "suspended":
                    logger.info(f"UISP suspended service for unit {unit_number}")

                    # Suspend ONU
                    if property_address:
                        self.onu_provisioner.suspend_onu(
                            property_address, unit_number,
                            reason="Non-payment - suspended by UISP"
                        )

                    # Create prorated credit in Innago
                    self._create_prorate_credit(lease_record, service)

                    # Update local status
                    self.db.update_service_status(lease_record["innago_lease_id"], "suspended")
                    self.db.log_event("service_suspended", f"Unit {unit_number} - non-payment")

                # UISP reactivated service (payment received)
                elif uisp_status == 1 and current_status == "suspended":
                    logger.info(f"UISP reactivated service for unit {unit_number}")

                    # Activate ONU
                    if property_address:
                        self.onu_provisioner.activate_onu(property_address, unit_number)

                    # Update local status
                    self.db.update_service_status(lease_record["innago_lease_id"], "active")
                    self.db.log_event("service_reactivated", f"Unit {unit_number} - payment received")

            except Exception as e:
                logger.error(f"Error checking UISP status for service {uisp_service_id}: {e}")

    def _create_prorate_credit(self, lease_record: dict, uisp_service: dict):
        """Create prorated credit in Innago when service is suspended mid-cycle."""
        try:
            # Calculate days remaining in billing cycle
            from datetime import datetime, timedelta

            # Get suspension date and billing period from UISP
            suspended_at = uisp_service.get("suspendedAt") or datetime.now().isoformat()
            if isinstance(suspended_at, str):
                suspended_date = datetime.fromisoformat(suspended_at.replace("Z", "+00:00"))
            else:
                suspended_date = datetime.now()

            # Assume monthly billing, calculate days remaining
            days_in_month = 30
            day_of_month = suspended_date.day
            days_remaining = days_in_month - day_of_month

            if days_remaining <= 0:
                return  # No prorate needed

            # Get package price
            package_name = lease_record.get("current_package", "Village Fiber 500")
            package = self.get_package_by_name(package_name)
            if not package:
                return

            monthly_rate = package.get("base_price", 45)
            daily_rate = monthly_rate / days_in_month
            credit_amount = round(daily_rate * days_remaining, 2)

            if credit_amount < 1:
                return  # Skip tiny credits

            # Create credit in Innago
            lease_id = lease_record.get("innago_lease_id")
            # Note: Innago API may use negative amount or separate credit endpoint
            self.innago.create_invoice(
                tenant_id=lease_record.get("innago_tenant_id"),
                line_items=[{
                    "description": f"Internet credit - service suspended {suspended_date.strftime('%m/%d')} ({days_remaining} days)",
                    "amount": -credit_amount  # Negative for credit
                }]
            )

            logger.info(f"Created ${credit_amount} prorate credit for unit {lease_record.get('unit_number')}")

        except Exception as e:
            logger.error(f"Error creating prorate credit: {e}")

    def sync_maintenance_tickets(self):
        """Check for internet-related maintenance tickets."""
        logger.info("Checking for maintenance tickets...")

        tickets = self.innago.get_maintenance_tickets(
            property_id=self.config.innago_property_id,
            status="open"
        )

        for ticket in tickets:
            ticket_id = str(ticket.get("id"))

            # Skip if already synced
            if self.db.is_ticket_synced(ticket_id):
                continue

            subject = ticket.get("subject", "").lower()
            description = ticket.get("description", "").lower()
            combined_text = f"{subject} {description}"

            # Check for upgrade keywords first
            if self._matches_keywords(combined_text, self.config.upgrade_keywords):
                self._handle_upgrade_request(ticket)
            # Then check for support keywords
            elif self._matches_keywords(combined_text, self.config.internet_keywords):
                self._handle_support_ticket(ticket)

    def _handle_support_ticket(self, ticket: dict):
        """Create a support ticket in UISP."""
        ticket_id = str(ticket.get("id"))
        unit_number = self._extract_unit_from_ticket(ticket)

        if not unit_number:
            logger.warning(f"Could not determine unit for ticket {ticket_id}")
            return

        # Find UISP client for this unit
        uisp_client_id = self._get_uisp_client_for_unit(unit_number)
        if not uisp_client_id:
            logger.warning(f"No UISP client found for unit {unit_number}")
            return

        try:
            uisp_ticket = self.uisp_crm.create_ticket(
                client_id=uisp_client_id,
                subject=f"[Innago #{ticket_id}] {ticket.get('subject', 'Internet Issue')}",
                message=ticket.get("description", "No description provided")
            )

            self.db.save_synced_ticket(ticket_id, str(uisp_ticket.get("id")), "support")
            self.db.log_event("ticket_synced", f"Innago {ticket_id} -> UISP {uisp_ticket.get('id')}")
            logger.info(f"Created UISP ticket for Innago ticket {ticket_id}")

        except Exception as e:
            logger.error(f"Failed to create UISP ticket: {e}")

    def _handle_upgrade_request(self, ticket: dict):
        """Handle a package upgrade request."""
        ticket_id = str(ticket.get("id"))
        unit_number = self._extract_unit_from_ticket(ticket)

        if not unit_number:
            logger.warning(f"Could not determine unit for upgrade ticket {ticket_id}")
            return

        # Determine requested package
        text = f"{ticket.get('subject', '')} {ticket.get('description', '')}".lower()
        new_package = None

        if "2g" in text or "2000" in text:
            new_package = next((p for p in self.config.packages if "2G" in p["name"]), None)
        elif "1g" in text or "1000" in text:
            new_package = next((p for p in self.config.packages if "1G" in p["name"]), None)

        if not new_package:
            logger.info(f"Could not determine package for upgrade ticket {ticket_id}")
            return

        # Get sync record for this unit
        sync_record = self._get_sync_record_for_unit(unit_number)
        if not sync_record:
            logger.warning(f"No sync record for unit {unit_number}")
            return

        try:
            # Update service plan in UISP
            plan_id = self.get_plan_id_for_package(new_package)
            if plan_id:
                self.uisp_crm.update_service(
                    sync_record["uisp_service_id"],
                    {"servicePlanId": int(plan_id)}
                )
                logger.info(f"Upgraded unit {unit_number} to {new_package['name']}")

            # Update Innago recurring charge
            if sync_record.get("innago_charge_id"):
                self.innago.update_recurring_charge(
                    charge_id=sync_record["innago_charge_id"],
                    amount=new_package["base_price"],
                    description=f"Internet - {new_package['name']}"
                )
                logger.info(f"Updated Innago charge to ${new_package['base_price']}")

                # Update local record
                self.db.update_lease_package(
                    lease_id=sync_record["innago_lease_id"],
                    innago_charge_id=sync_record["innago_charge_id"],
                    package_name=new_package["name"]
                )

            self.db.save_synced_ticket(ticket_id, "", "upgrade")
            self.db.log_event("upgrade_processed", f"Unit {unit_number} -> {new_package['name']}")

        except Exception as e:
            logger.error(f"Failed to process upgrade: {e}")

    def _extract_unit_number(self, lease: dict) -> str | None:
        """Extract unit number from lease data."""
        # Try various fields where unit number might be
        unit = lease.get("unitNumber") or lease.get("unit", {}).get("number")
        if unit:
            return str(unit)

        # Try to extract from unit name
        unit_name = lease.get("unit", {}).get("name", "")
        match = re.search(r"(\d+)", unit_name)
        if match:
            return match.group(1)

        return None

    def _extract_property_address(self, lease: dict) -> str | None:
        """Extract property address from lease data for ONU mapping."""
        # Try property.address field
        property_info = lease.get("property", {})
        address = property_info.get("address") or property_info.get("name")
        if address:
            return address

        # Try unit.property.address
        unit_info = lease.get("unit", {})
        property_info = unit_info.get("property", {})
        address = property_info.get("address") or property_info.get("name")
        if address:
            return address

        # Try top-level address fields
        address = lease.get("propertyAddress") or lease.get("address")
        if address:
            return address

        return None

    def _extract_unit_from_ticket(self, ticket: dict) -> str | None:
        """Extract unit number from maintenance ticket."""
        # Check if ticket has unit info
        unit = ticket.get("unitNumber") or ticket.get("unit", {}).get("number")
        if unit:
            return str(unit)

        # Try to extract from subject/description
        text = f"{ticket.get('subject', '')} {ticket.get('description', '')}"
        match = re.search(r"unit\s*#?\s*(\d+)", text, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def _matches_keywords(self, text: str, keywords: list) -> bool:
        """Check if text contains any of the keywords."""
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)

    def _get_or_create_site(self, unit_number: str) -> dict:
        """Get or create a subscriber site for the unit."""
        site_name = f"Unit {unit_number}"

        # Check if site exists
        sites = self.uisp_nms.get_sites(parent_id=self.config.uisp_parent_site_id)
        for site in sites:
            if site.get("name") == site_name:
                return site

        # Create new site
        return self.uisp_nms.create_site(
            name=site_name,
            parent_site_id=self.config.uisp_parent_site_id,
            site_type="endpoint"
        )

    def _assign_onu_to_unit(self, unit_number: str, site: dict, property_address: str = None):
        """Find ONU for unit and activate it."""
        # Use the ONU inventory to find and activate the ONU
        # Property address should be like "350 S Harper" or extracted from site/lease

        if not property_address:
            # Try to extract from site name or use a default
            # Site name is typically "Unit X" so we need the property from elsewhere
            logger.warning(f"No property address provided for unit {unit_number}")
            return False

        try:
            activated = self.onu_provisioner.activate_onu(property_address, unit_number)
            if activated:
                logger.info(f"Activated ONU for {property_address} unit {unit_number}")
            else:
                logger.warning(f"Could not activate ONU for {property_address} unit {unit_number}")
            return activated
        except Exception as e:
            logger.error(f"Error activating ONU for unit {unit_number}: {e}")
            return False

    def _get_uisp_client_for_unit(self, unit_number: str) -> str | None:
        """Get UISP client ID for a unit."""
        sync_record = self._get_sync_record_for_unit(unit_number)
        return sync_record.get("uisp_client_id") if sync_record else None

    def _get_sync_record_for_unit(self, unit_number: str) -> dict | None:
        """Get sync record for a unit number."""
        # Query database for the unit
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM synced_leases WHERE unit_number = ?",
                (unit_number,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
