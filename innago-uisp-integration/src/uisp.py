import requests
from typing import Optional


class UispCrmClient:
    """Client for UISP CRM API."""

    def __init__(self, host: str, api_key: str):
        self.base_url = f"http://{host}/crm/api/v1.0"
        self.session = requests.Session()
        self.session.headers.update({
            "X-Auth-App-Key": api_key,
            "Content-Type": "application/json"
        })

    def _get(self, endpoint: str, params: dict = None) -> dict:
        resp = self.session.get(f"{self.base_url}{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint: str, data: dict) -> dict:
        resp = self.session.post(f"{self.base_url}{endpoint}", json=data)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, endpoint: str, data: dict) -> dict:
        resp = self.session.patch(f"{self.base_url}{endpoint}", json=data)
        resp.raise_for_status()
        return resp.json()

    # Clients
    def get_clients(self) -> list:
        """Get all clients."""
        return self._get("/clients")

    def get_client(self, client_id: str) -> dict:
        """Get a specific client."""
        return self._get(f"/clients/{client_id}")

    def create_client(self, first_name: str, last_name: str, email: str,
                      street: str = "", city: str = "", zip_code: str = "",
                      note: str = "") -> dict:
        """Create a new client."""
        return self._post("/clients", {
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "street1": street,
            "city": city,
            "zipCode": zip_code,
            "note": note,
            "isLead": False
        })

    def update_client(self, client_id: str, data: dict) -> dict:
        """Update a client."""
        return self._patch(f"/clients/{client_id}", data)

    # Services
    def get_services(self, client_id: Optional[str] = None) -> list:
        """Get services, optionally filtered by client."""
        params = {}
        if client_id:
            params["clientId"] = client_id
        return self._get("/services", params)

    def create_service(self, client_id: str, service_plan_id: str,
                       active_from: str, note: str = "") -> dict:
        """Create a service for a client."""
        return self._post("/services", {
            "clientId": int(client_id),
            "servicePlanId": int(service_plan_id),
            "activeFrom": active_from,
            "note": note,
            "status": 1  # Active
        })

    def update_service(self, service_id: str, data: dict) -> dict:
        """Update a service (e.g., change plan)."""
        return self._patch(f"/services/{service_id}", data)

    # Service Plans
    def get_service_plans(self) -> list:
        """Get all service plans."""
        return self._get("/service-plans")

    # Tickets
    def get_tickets(self, client_id: Optional[str] = None) -> list:
        """Get tickets."""
        params = {}
        if client_id:
            params["clientId"] = client_id
        return self._get("/tickets", params)

    def create_ticket(self, client_id: str, subject: str, message: str) -> dict:
        """Create a support ticket for a client."""
        return self._post("/tickets", {
            "clientId": int(client_id),
            "subject": subject,
            "message": message
        })

    def create_ticket_for_device(self, subject: str, message: str, device_id: str = None) -> dict:
        """
        Create a support ticket linked to a device (ONU).

        Uses the Victorian Village master client for all tickets,
        with device info in the ticket body.
        """
        # Get or create the Victorian Village master client
        vic_vil_client_id = self._get_vic_vil_client_id()

        ticket_data = {
            "clientId": vic_vil_client_id,
            "subject": subject,
            "message": message,
        }

        # Add device reference if available
        if device_id:
            ticket_data["deviceId"] = device_id

        return self._post("/tickets", ticket_data)

    def _get_vic_vil_client_id(self) -> int:
        """Get or create the Victorian Village master client for tickets."""
        # Search for existing client
        clients = self._get("/clients")
        for client in clients:
            if "Victorian Village" in client.get("companyName", ""):
                return int(client.get("id"))
            if "Victorian Village" in f"{client.get('firstName', '')} {client.get('lastName', '')}":
                return int(client.get("id"))

        # Create if not found
        new_client = self._post("/clients", {
            "companyName": "Victorian Village Apartments",
            "firstName": "Property",
            "lastName": "Management",
            "isLead": False,
            "note": "Master client for Victorian Village internet tickets"
        })
        return int(new_client.get("id"))

    # Billing for apartment complex
    def get_or_create_billing_client(self, company_name: str, email: str,
                                      contact_name: str = None) -> dict:
        """
        Get or create a billing client for the apartment complex.
        This client gets invoices and can access the UISP portal.
        """
        # Search for existing
        clients = self._get("/clients")
        for client in clients:
            if client.get("companyName") == company_name:
                return client

        # Create new billing client
        first_name = "Property"
        last_name = "Management"
        if contact_name:
            parts = contact_name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

        return self._post("/clients", {
            "companyName": company_name,
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "isLead": False,
            "sendInvoiceByEmail": True,
            "invoiceMaturityDays": 14,
            "note": "Apartment complex billing - monthly internet service"
        })

    def create_invoice(self, client_id: int, items: list, due_days: int = 14) -> dict:
        """
        Create an invoice for the apartment complex.

        items: list of {"description": str, "quantity": int, "price": float}
        """
        from datetime import datetime, timedelta

        invoice_date = datetime.now().strftime("%Y-%m-%d")
        due_date = (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d")

        return self._post("/invoices", {
            "clientId": client_id,
            "createdDate": invoice_date,
            "dueDate": due_date,
            "items": items
        })

    def create_monthly_invoice(self, client_id: int, occupied_units: int,
                                base_rate: float, upgrades: dict = None) -> dict:
        """
        Create monthly invoice for apartment complex.

        upgrades: {"VIC-VIL 1G": count, "VIC-VIL 2G": count}
        """
        items = [{
            "description": f"Internet Service - {occupied_units} occupied units @ ${base_rate}/unit",
            "quantity": occupied_units,
            "price": base_rate
        }]

        # Add upgrade line items
        if upgrades:
            if upgrades.get("VIC-VIL 1G", 0) > 0:
                items.append({
                    "description": "1G Upgrade Add-on",
                    "quantity": upgrades["VIC-VIL 1G"],
                    "price": 10.00
                })
            if upgrades.get("VIC-VIL 2G", 0) > 0:
                items.append({
                    "description": "2G Upgrade Add-on",
                    "quantity": upgrades["VIC-VIL 2G"],
                    "price": 20.00
                })

        return self.create_invoice(client_id, items)


class UispNmsClient:
    """Client for UISP NMS API."""

    def __init__(self, host: str, api_key: str):
        self.base_url = f"http://{host}/nms/api/v2.1"
        self.session = requests.Session()
        self.session.headers.update({
            "x-auth-token": api_key,
            "Content-Type": "application/json"
        })

    def _get(self, endpoint: str, params: dict = None) -> dict:
        resp = self.session.get(f"{self.base_url}{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint: str, data: dict) -> dict:
        resp = self.session.post(f"{self.base_url}{endpoint}", json=data)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, endpoint: str, data: dict) -> dict:
        resp = self.session.patch(f"{self.base_url}{endpoint}", json=data)
        resp.raise_for_status()
        return resp.json()

    # Devices
    def get_devices(self, site_id: Optional[str] = None) -> list:
        """Get all devices, optionally filtered by site."""
        params = {}
        if site_id:
            params["siteId"] = site_id
        return self._get("/devices", params)

    def get_device(self, device_id: str) -> dict:
        """Get a specific device."""
        return self._get(f"/devices/{device_id}")

    def update_device(self, device_id: str, data: dict) -> dict:
        """Update a device (e.g., rename)."""
        return self._patch(f"/devices/{device_id}", data)

    def rename_device(self, device_id: str, name: str) -> dict:
        """Rename a device."""
        return self.update_device(device_id, {"identification": {"name": name}})

    # Sites
    def get_sites(self, parent_id: Optional[str] = None) -> list:
        """Get all sites."""
        params = {}
        if parent_id:
            params["parentSiteId"] = parent_id
        return self._get("/sites", params)

    def get_site(self, site_id: str) -> dict:
        """Get a specific site."""
        return self._get(f"/sites/{site_id}")

    def create_site(self, name: str, parent_site_id: str,
                    site_type: str = "endpoint") -> dict:
        """Create a subscriber site."""
        return self._post("/sites", {
            "name": name,
            "parentSiteId": parent_site_id,
            "type": site_type
        })

    def assign_device_to_site(self, device_id: str, site_id: str) -> dict:
        """Assign a device to a site."""
        return self.update_device(device_id, {"siteId": site_id})

    def suspend_device(self, device_id: str, reason: str = "Awaiting tenant") -> dict:
        """Suspend/disable a device (ONU stays registered but inactive)."""
        return self.update_device(device_id, {
            "enabled": False,
            "attributes": {
                "suspended": True,
                "suspendedReason": reason
            }
        })

    def activate_device(self, device_id: str) -> dict:
        """Activate a suspended device."""
        return self.update_device(device_id, {
            "enabled": True,
            "attributes": {
                "suspended": False,
                "suspendedReason": None
            }
        })

    def find_device_by_serial(self, serial: str) -> Optional[dict]:
        """Find device by serial number or MAC."""
        devices = self.get_devices()
        serial_lower = serial.lower().replace(':', '')
        for d in devices:
            ident = d.get('identification', {})
            device_serial = ident.get('serialNumber', '').lower()
            device_mac = ident.get('mac', '').lower().replace(':', '')
            if serial_lower in [device_serial, device_mac]:
                return d
        return None

    def authorize_device(self, device_id: str, name: str, site_id: str = None) -> dict:
        """Authorize a device with a name and optionally assign to site."""
        data = {
            "identification": {
                "name": name,
                "authorized": True
            }
        }
        if site_id:
            data["identification"]["siteId"] = site_id
        return self.update_device(device_id, data)

    def set_device_qos(self, device_id: str, download_mbps: int, upload_mbps: int) -> dict:
        """Set bandwidth limits (QoS) on a device."""
        # Convert Mbps to bps for UISP API
        download_bps = download_mbps * 1_000_000
        upload_bps = upload_mbps * 1_000_000

        return self.update_device(device_id, {
            "qos": {
                "enabled": True,
                "downloadSpeed": download_bps,
                "uploadSpeed": upload_bps
            }
        })

    def remove_device_qos(self, device_id: str) -> dict:
        """Remove bandwidth limits from a device."""
        return self.update_device(device_id, {
            "qos": {
                "enabled": False
            }
        })
