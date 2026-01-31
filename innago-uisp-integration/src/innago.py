import requests
from typing import Optional


class InnagoClient:
    """Client for Innago Property Management API."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "x-api-key": api_key,
            "Content-Type": "application/json"
        })

    def _get(self, endpoint: str, params: dict = None) -> dict:
        resp = self.session.get(f"{self.api_url}{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint: str, data: dict) -> dict:
        resp = self.session.post(f"{self.api_url}{endpoint}", json=data)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, endpoint: str, data: dict) -> dict:
        resp = self.session.patch(f"{self.api_url}{endpoint}", json=data)
        resp.raise_for_status()
        return resp.json()

    # Properties & Units
    def get_properties(self) -> list:
        """Get all properties."""
        return self._get("/v1/properties")

    def get_units(self, property_id: str) -> list:
        """Get all units for a property."""
        return self._get(f"/v1/properties/{property_id}/units")

    # Leases & Tenants
    def get_leases(self, property_id: Optional[str] = None,
                   status: Optional[str] = None) -> list:
        """Get all leases, optionally filtered by property and status."""
        params = {}
        if property_id:
            params["propertyId"] = property_id
        if status:
            params["status"] = status
        return self._get("/v1/leases", params)

    def get_tenants_by_lease(self, lease_id: str) -> list:
        """Get tenants for a specific lease."""
        return self._get("/v1/tenants", params={"leaseId": lease_id})

    def get_tenant(self, tenant_id: str) -> dict:
        """Get a specific tenant."""
        return self._get(f"/v1/tenants/{tenant_id}")

    # Maintenance Tickets
    def get_maintenance_tickets(self, property_id: Optional[str] = None,
                                 status: Optional[str] = None) -> list:
        """Get maintenance tickets."""
        params = {}
        if property_id:
            params["propertyId"] = property_id
        if status:
            params["status"] = status
        return self._get("/v1/maintenance", params)

    def create_maintenance_ticket(self, data: dict) -> dict:
        """Create a maintenance ticket."""
        return self._post("/v1/maintenance", data)

    def update_ticket_status(self, ticket_id: str, status: str) -> dict:
        """Update ticket status."""
        return self._patch(f"/v1/maintenance/{ticket_id}/status", {"status": status})

    # Invoices
    def get_invoices(self, tenant_id: Optional[str] = None) -> list:
        """Get invoices."""
        params = {}
        if tenant_id:
            params["tenantId"] = tenant_id
        return self._get("/v1/invoices", params)

    def create_invoice(self, tenant_id: str, line_items: list) -> dict:
        """Create an invoice for a tenant."""
        return self._post("/v1/invoices", {
            "tenantId": tenant_id,
            "lineItems": line_items
        })

    # Recurring Charges
    def get_recurring_charges(self, lease_id: str) -> list:
        """Get recurring charges for a lease."""
        return self._get("/v1/recurring-charges", params={"leaseId": lease_id})

    def create_recurring_charge(self, lease_id: str, description: str,
                                 amount: float, category: str = "Utilities") -> dict:
        """Create a recurring charge for a lease."""
        return self._post("/v1/recurring-charges", {
            "leaseId": lease_id,
            "description": description,
            "amount": amount,
            "category": category
        })

    def update_recurring_charge(self, charge_id: str, amount: float,
                                 description: str = None) -> dict:
        """Update a recurring charge."""
        data = {"amount": amount}
        if description:
            data["description"] = description
        return self._patch(f"/v1/recurring-charges/{charge_id}", data)

    def delete_recurring_charge(self, charge_id: str) -> dict:
        """Delete a recurring charge."""
        resp = self.session.delete(f"{self.api_url}/v1/recurring-charges/{charge_id}")
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    # Lease Balance (for rent delinquency checking)
    def get_lease_balance(self, lease_id: str) -> float:
        """
        Get outstanding balance for a lease.
        Returns amount owed (0 if paid up, >0 if owes money).
        """
        try:
            # Try to get lease balance directly
            lease = self._get(f"/v1/leases/{lease_id}")
            balance = lease.get("balance") or lease.get("outstandingBalance") or 0
            return float(balance)
        except Exception:
            pass

        # Fallback: sum unpaid invoices
        try:
            invoices = self._get("/v1/invoices", params={"leaseId": lease_id})
            total_owed = 0
            for inv in invoices:
                if inv.get("status") in ["unpaid", "partially_paid", "overdue"]:
                    amount = float(inv.get("amount", 0))
                    paid = float(inv.get("amountPaid", 0))
                    total_owed += (amount - paid)
            return total_owed
        except Exception:
            return 0

    def get_lease(self, lease_id: str) -> dict:
        """Get a specific lease."""
        return self._get(f"/v1/leases/{lease_id}")
