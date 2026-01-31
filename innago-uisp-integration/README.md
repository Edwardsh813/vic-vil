# Victorian Village - Innago/UISP Integration

## Billing Model

ERE Fiber bills the apartment complex monthly based on occupied units. Internet is included in rent - tenants don't receive separate bills from ERE.

```
Monthly Invoice to Complex = Occupied Units × $45

Example:
- 113 units occupied → Complex pays $5,085
- Unit vacates → Next month drops to 112 × $45 = $5,040
- New tenant moves in → Billing auto-adjusts
```

## What This Integration Does

1. **Activates ONU when lease starts** - New lease in Innago → ONU activated
2. **Suspends ONU when lease ends** - Lease ends → ONU suspended (unit vacant)
3. **Suspends for rent delinquency** - Rent not paid by 5th → ONU suspended
4. **Reactivates after payment** - Rent paid → ONU reactivated
5. **Forwards internet tickets** - Internet issues in Innago → Forwarded to UISP
6. **Generates billing reports** - Monthly count of occupied units for invoicing

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     INNAGO (Property Mgmt)                       │
│  - Tracks leases (move-in/move-out)                             │
│  - Tracks rent payments                                          │
│  - Receives maintenance tickets                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Poll every 5 min
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     VIC-VIL SYNC SERVICE                         │
│                                                                  │
│  sync_leases()           → Activate/suspend ONU on move-in/out  │
│  check_rent_delinquency() → Suspend ONU if rent unpaid by 5th   │
│  sync_maintenance_tickets() → Forward internet issues to UISP  │
│  generate_billing_report() → Monthly invoice for complex        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     UISP NMS (10.8.10.10)                        │
│  - Controls ONUs (activate/suspend)                              │
│  - Receives forwarded tickets                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Rent Collection Leverage

Internet suspension is a powerful tool for rent collection:

```
Rent due: 1st of month
Grace period: Through 5th
After 5th: If balance > $0 → Internet suspended
Payment received: Internet restored automatically
```

The complex pays ERE the flat monthly rate regardless - the suspension is just leverage to help collect rent.

## Usage

```bash
# Run continuously (polls every 5 min)
python main.py

# Run once and exit
python main.py --once

# Generate billing report
python main.py --billing

# Show unit status
python main.py --status
```

## Configuration

```yaml
# config.yaml
innago:
  api_url: https://api-my.innago.com/openapi
  api_key: <YOUR_KEY>
  property_id: <PROPERTY_ID>

uisp:
  host: 10.8.10.10
  nms_api_key: <YOUR_KEY>
  parent_site_id: <SITE_ID>

billing:
  base_rate: 45         # Per occupied unit
  total_units: 118
  grace_period_day: 5   # Suspend after this day if rent unpaid

keywords:
  internet_issues:
    - internet
    - wifi
    - fiber
    - slow
    - outage
```

## Billing Report Output

```
ERE Fiber - Victorian Village - 1/2026
==================================================
Occupied Units:    113 / 118
Vacant Units:      5

Base Rate:         $45.00/unit
==================================================
TOTAL DUE:         $5,085.00
==================================================
```

## Requirements

- Python 3.10+
- Innago API key
- UISP NMS API key
- ONU inventory CSV (maps units to ONUs)

## Installation

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
# Edit config.yaml with your keys
python main.py
```

## To Do

- [ ] Get Innago API key
- [ ] Confirm Innago property ID
- [ ] Test with single unit
- [ ] Deploy as systemd service
