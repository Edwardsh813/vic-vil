"""
ONU Inventory Management

Handles the onu-inventory.csv file for mapping ONUs to units.
Provides functions to provision, activate, and suspend ONUs.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

INVENTORY_FILE = Path(__file__).parent.parent / 'onu-inventory.csv'

FIELDNAMES = [
    'onu_name', 'serial_number', 'mac_address', 'property', 'unit',
    'date_added', 'status', 'uisp_id'
]


def load_inventory() -> list[dict]:
    """Load ONU inventory from CSV."""
    if not INVENTORY_FILE.exists():
        return []
    with open(INVENTORY_FILE, 'r') as f:
        return list(csv.DictReader(f))


def save_inventory(rows: list[dict]):
    """Save ONU inventory to CSV."""
    with open(INVENTORY_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def find_onu_by_unit(property_name: str, unit: str) -> Optional[dict]:
    """
    Find ONU by property and unit.

    Matches:
      - property "350 S Harper" + unit "1" -> onu_name "350-s-harper-1"
      - Or direct match on property and unit columns
    """
    inventory = load_inventory()

    # Normalize property name: "350 S Harper" -> "350-s-harper"
    prop_normalized = property_name.lower().replace(' ', '-')
    unit_str = str(unit)

    for row in inventory:
        # Match by property + unit columns
        row_prop = row['property'].lower().replace(' ', '-')
        if row_prop == prop_normalized and row['unit'] == unit_str:
            return row

        # Match by onu_name directly
        expected_name = f"{prop_normalized}-{unit_str}"
        if row['onu_name'] == expected_name:
            return row

    return None


def find_onu_by_name(onu_name: str) -> Optional[dict]:
    """Find ONU by name."""
    inventory = load_inventory()
    return next((r for r in inventory if r['onu_name'] == onu_name), None)


def update_onu_status(onu_name: str, status: str, uisp_id: str = None):
    """Update ONU status in inventory."""
    inventory = load_inventory()

    for row in inventory:
        if row['onu_name'] == onu_name:
            row['status'] = status
            if uisp_id:
                row['uisp_id'] = uisp_id
            if status in ['suspended', 'active'] and not row['date_added']:
                row['date_added'] = datetime.now().strftime('%Y-%m-%d')
            break

    save_inventory(inventory)


def generate_onu_name(property_name: str, unit: str) -> str:
    """Generate ONU name from property and unit."""
    # "350 S Harper" + "1" -> "350-s-harper-1"
    name = property_name.lower().replace(' ', '-')
    return f"{name}-{unit}"


def get_pending_onus() -> list[dict]:
    """Get ONUs with serial numbers that need provisioning."""
    inventory = load_inventory()
    return [r for r in inventory if r['serial_number'] and r['status'] == 'pending']


def get_all_onus_status() -> list[dict]:
    """Get status summary of all ONUs."""
    inventory = load_inventory()
    return [{
        'onu_name': r['onu_name'],
        'property': r['property'],
        'unit': r['unit'],
        'status': r['status'],
        'has_serial': bool(r['serial_number']),
        'provisioned': bool(r['uisp_id'])
    } for r in inventory]


class ONUProvisioner:
    """Handles ONU provisioning to UISP."""

    def __init__(self, uisp_nms_client, site_id: str):
        self.uisp = uisp_nms_client
        self.site_id = site_id

    def provision_onu(self, onu_name: str, serial: str) -> bool:
        """
        Provision an ONU to UISP (suspended).

        1. Find ONU in UISP by serial
        2. Authorize with name
        3. Assign to site
        4. Suspend (awaiting tenant)
        5. Update inventory
        """
        logger.info(f"Provisioning ONU: {onu_name} (serial: {serial})")

        # Find device in UISP
        device = self.uisp.find_device_by_serial(serial)
        if not device:
            logger.warning(f"ONU not found in UISP: {serial}")
            return False

        device_id = device.get('id')
        logger.info(f"Found device in UISP: {device_id}")

        try:
            # Authorize with name and assign to site
            self.uisp.authorize_device(device_id, onu_name, self.site_id)
            logger.info(f"Authorized as: {onu_name}")

            # Suspend until tenant activates
            self.uisp.suspend_device(device_id, "Awaiting tenant - Innago integration")
            logger.info(f"Suspended (awaiting tenant)")

            # Update inventory
            update_onu_status(onu_name, 'suspended', device_id)

            return True

        except Exception as e:
            logger.error(f"Failed to provision {onu_name}: {e}")
            return False

    def provision_all_pending(self) -> dict:
        """Provision all pending ONUs with serial numbers."""
        pending = get_pending_onus()
        results = {'success': 0, 'failed': 0, 'not_found': 0}

        for onu in pending:
            if self.provision_onu(onu['onu_name'], onu['serial_number']):
                results['success'] += 1
            else:
                results['failed'] += 1

        return results

    def activate_onu(self, property_name: str, unit: str,
                     download_mbps: int = 500, upload_mbps: int = 500) -> bool:
        """Activate ONU for a unit with bandwidth limits (called when lease starts)."""
        onu = find_onu_by_unit(property_name, unit)

        if not onu:
            logger.warning(f"No ONU found for {property_name} unit {unit}")
            return False

        if not onu['uisp_id']:
            logger.warning(f"ONU {onu['onu_name']} not provisioned yet")
            return False

        try:
            # Activate the device
            self.uisp.activate_device(onu['uisp_id'])

            # Apply bandwidth limits
            self.uisp.set_device_qos(onu['uisp_id'], download_mbps, upload_mbps)
            logger.info(f"Set QoS on {onu['onu_name']}: {download_mbps}/{upload_mbps} Mbps")

            update_onu_status(onu['onu_name'], 'active')
            logger.info(f"Activated ONU: {onu['onu_name']}")
            return True
        except Exception as e:
            logger.error(f"Failed to activate {onu['onu_name']}: {e}")
            return False

    def set_onu_speed(self, property_name: str, unit: str,
                      download_mbps: int, upload_mbps: int) -> bool:
        """Update bandwidth limits on an ONU (for upgrades)."""
        onu = find_onu_by_unit(property_name, unit)

        if not onu or not onu['uisp_id']:
            logger.warning(f"No provisioned ONU found for {property_name} unit {unit}")
            return False

        try:
            self.uisp.set_device_qos(onu['uisp_id'], download_mbps, upload_mbps)
            logger.info(f"Updated QoS on {onu['onu_name']}: {download_mbps}/{upload_mbps} Mbps")
            return True
        except Exception as e:
            logger.error(f"Failed to set speed on {onu['onu_name']}: {e}")
            return False

    def suspend_onu(self, property_name: str, unit: str, reason: str = "Tenant moved out") -> bool:
        """Suspend ONU for a unit (called when lease ends)."""
        onu = find_onu_by_unit(property_name, unit)

        if not onu:
            logger.warning(f"No ONU found for {property_name} unit {unit}")
            return False

        if not onu['uisp_id']:
            logger.warning(f"ONU {onu['onu_name']} not provisioned yet")
            return False

        if onu['status'] == 'suspended':
            logger.info(f"ONU {onu['onu_name']} already suspended")
            return True

        try:
            self.uisp.suspend_device(onu['uisp_id'], reason)
            update_onu_status(onu['onu_name'], 'suspended')
            logger.info(f"Suspended ONU: {onu['onu_name']}")
            return True
        except Exception as e:
            logger.error(f"Failed to suspend {onu['onu_name']}: {e}")
            return False
