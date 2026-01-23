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
        """Create a support ticket."""
        return self._post("/tickets", {
            "clientId": int(client_id),
            "subject": subject,
            "message": message
        })


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
