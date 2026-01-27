#!/usr/bin/env python3
"""
ERE Fiber ONU Provisioning CLI

Provision ONUs from onu-inventory.csv to UISP.
ONUs are added as suspended, awaiting tenant activation via Innago.

Usage:
    ./provision-onus.py list      # Show inventory status
    ./provision-onus.py discover  # Find unauthorized ONUs in UISP
    ./provision-onus.py provision # Provision all pending ONUs
    ./provision-onus.py activate <onu-name>   # Manually activate
    ./provision-onus.py suspend <onu-name>    # Manually suspend
"""

import sys
import argparse
import logging

# Setup path for imports
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

from src.config import Config
from src.uisp import UispNmsClient
from src.onu import (
    ONUProvisioner, load_inventory, get_pending_onus,
    get_all_onus_status, find_onu_by_name, update_onu_status
)

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def cmd_list(args, config):
    """List all ONUs and their status."""
    status = get_all_onus_status()

    print("\nONU Inventory Status")
    print("=" * 80)
    print(f"{'ONU Name':<25} {'Property':<15} {'Unit':<5} {'Status':<12} {'Ready'}")
    print("-" * 80)

    counts = {'pending': 0, 'suspended': 0, 'active': 0, 'no_serial': 0}

    for onu in status:
        ready = "Yes" if onu['has_serial'] else "Need serial"
        print(f"{onu['onu_name']:<25} {onu['property']:<15} {onu['unit']:<5} {onu['status']:<12} {ready}")

        if not onu['has_serial']:
            counts['no_serial'] += 1
        else:
            counts[onu['status']] = counts.get(onu['status'], 0) + 1

    print("-" * 80)
    print(f"Total: {len(status)} ONUs")
    print(f"  Need serial: {counts['no_serial']}")
    print(f"  Pending:     {counts['pending']}")
    print(f"  Suspended:   {counts['suspended']}")
    print(f"  Active:      {counts['active']}")
    print()


def cmd_discover(args, config):
    """Discover unauthorized ONUs in UISP."""
    uisp = UispNmsClient(config.uisp_host, config.uisp_nms_api_key)

    print("\nDiscovering ONUs in UISP...")

    try:
        devices = uisp.get_devices()
    except Exception as e:
        print(f"Error connecting to UISP: {e}")
        return

    # Filter for ONU/ONT devices
    onus = []
    for d in devices:
        ident = d.get('identification', {})
        model = ident.get('model', '').lower()
        name = ident.get('name', '')
        authorized = ident.get('authorized', True)

        if 'onu' in model or 'ont' in model or 'fiber' in model.lower():
            onus.append({
                'id': d.get('id'),
                'name': name,
                'serial': ident.get('serialNumber', ''),
                'mac': ident.get('mac', ''),
                'model': ident.get('model', ''),
                'authorized': authorized,
                'status': d.get('overview', {}).get('status', 'unknown')
            })

    if not onus:
        print("No ONU devices found in UISP.")
        return

    print(f"\nFound {len(onus)} ONU device(s):")
    print("-" * 90)
    print(f"{'Name':<25} {'Serial':<20} {'Model':<20} {'Auth':<6} {'Status'}")
    print("-" * 90)

    for onu in onus:
        auth = "Yes" if onu['authorized'] else "NO"
        print(f"{onu['name']:<25} {onu['serial']:<20} {onu['model']:<20} {auth:<6} {onu['status']}")

    # Show unauthorized ones
    unauth = [o for o in onus if not o['authorized']]
    if unauth:
        print(f"\n{len(unauth)} unauthorized ONU(s) ready for provisioning:")
        for o in unauth:
            print(f"  Serial: {o['serial']}  MAC: {o['mac']}")
    print()


def cmd_provision(args, config):
    """Provision all pending ONUs to UISP."""
    pending = get_pending_onus()

    if not pending:
        print("\nNo ONUs pending provisioning.")
        print("Add serial numbers to onu-inventory.csv first.")
        return

    print(f"\nProvisioning {len(pending)} ONU(s) to UISP...")
    print("=" * 60)

    uisp = UispNmsClient(config.uisp_host, config.uisp_nms_api_key)
    provisioner = ONUProvisioner(uisp, config.uisp_parent_site_id)

    results = provisioner.provision_all_pending()

    print("\nResults:")
    print(f"  Success:   {results['success']}")
    print(f"  Failed:    {results['failed']}")
    print()


def cmd_activate(args, config):
    """Manually activate an ONU."""
    onu = find_onu_by_name(args.onu_name)
    if not onu:
        print(f"ONU not found: {args.onu_name}")
        return

    if not onu['uisp_id']:
        print(f"ONU not provisioned to UISP yet: {args.onu_name}")
        return

    print(f"Activating {args.onu_name}...")

    uisp = UispNmsClient(config.uisp_host, config.uisp_nms_api_key)
    try:
        uisp.activate_device(onu['uisp_id'])
        update_onu_status(args.onu_name, 'active')
        print("Activated!")
    except Exception as e:
        print(f"Failed: {e}")


def cmd_suspend(args, config):
    """Manually suspend an ONU."""
    onu = find_onu_by_name(args.onu_name)
    if not onu:
        print(f"ONU not found: {args.onu_name}")
        return

    if not onu['uisp_id']:
        print(f"ONU not provisioned to UISP yet: {args.onu_name}")
        return

    print(f"Suspending {args.onu_name}...")

    uisp = UispNmsClient(config.uisp_host, config.uisp_nms_api_key)
    try:
        uisp.suspend_device(onu['uisp_id'], args.reason or "Manual suspension")
        update_onu_status(args.onu_name, 'suspended')
        print("Suspended!")
    except Exception as e:
        print(f"Failed: {e}")


def main():
    parser = argparse.ArgumentParser(description='ERE Fiber ONU Provisioning')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List
    subparsers.add_parser('list', help='List all ONUs and status')

    # Discover
    subparsers.add_parser('discover', help='Discover unauthorized ONUs in UISP')

    # Provision
    subparsers.add_parser('provision', help='Provision pending ONUs to UISP')

    # Activate
    p_activate = subparsers.add_parser('activate', help='Activate an ONU')
    p_activate.add_argument('onu_name', help='ONU name (e.g., 350-s-harper-1)')

    # Suspend
    p_suspend = subparsers.add_parser('suspend', help='Suspend an ONU')
    p_suspend.add_argument('onu_name', help='ONU name (e.g., 350-s-harper-1)')
    p_suspend.add_argument('--reason', help='Suspension reason')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load config
    try:
        config = Config()
    except Exception as e:
        print(f"Error loading config: {e}")
        print("Make sure config.yaml exists with UISP settings.")
        return

    # Run command
    if args.command == 'list':
        cmd_list(args, config)
    elif args.command == 'discover':
        cmd_discover(args, config)
    elif args.command == 'provision':
        cmd_provision(args, config)
    elif args.command == 'activate':
        cmd_activate(args, config)
    elif args.command == 'suspend':
        cmd_suspend(args, config)


if __name__ == '__main__':
    main()
