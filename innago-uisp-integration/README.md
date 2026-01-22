# Victorian Village - Innago/UISP Integration

## Overview

Integration between Innago (property management) and UISP (ERE Fiber network management) for the 118-unit Victorian Village complex.

**Status:** Waiting on API keys

## Goals

1. Auto-provision Village Fiber service when new lease starts
2. Add fiber charges to Innago invoices
3. Forward internet-related maintenance tickets from Innago to UISP
4. Allow tenants to upgrade packages via Innago maintenance requests
5. Name ONUs by apartment number and link to units in UISP

---

## API Endpoints

### Innago API
- **Base URL:** `https://api-my.innago.com/openapi`
- **Auth:** Bearer token or `x-api-key` header
- **Docs:** https://docs.innago.com/reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/tenants` | GET | Get all tenants by lease ID |
| `/v1/tenants/{tenantId}` | GET | Get specific tenant |
| `/v1/leases` | GET | Get all leases by property/unit |
| `/v1/invoices` | POST | Create invoice for tenant |
| `/v1/invoices` | GET | Get all invoices |
| `/v1/properties` | GET | Get all properties |
| `/v1/properties/{id}/units` | GET | Get units for a property |
| `/v1/maintenance` | GET | Get all maintenance tickets |
| `/v1/maintenance` | POST | Create maintenance ticket |
| `/v1/maintenance/{id}/status` | PATCH | Update ticket status |

### UISP CRM API
- **Base URL:** `http://10.8.10.10/crm/api/v1.0/`
- **Auth:** `X-Auth-App-Key` header
- **Docs:** `http://10.8.10.10/crm/api-docs/`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/clients` | POST | Create customer |
| `/clients` | GET | List customers |
| `/clients/{id}` | PATCH | Update customer |
| `/services` | POST | Create service |
| `/services/{id}` | PATCH | Update service (plan changes) |
| `/tickets` | POST | Create support ticket |

### UISP NMS API
- **Base URL:** `http://10.8.10.10/nms/api/v2.1/`
- **Auth:** `x-auth-token` header
- **Docs:** `http://10.8.10.10/nms/api-docs/`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/devices` | GET | List devices |
| `/devices/{id}` | PATCH | Update device (rename) |
| `/sites` | GET | List sites |
| `/sites` | POST | Create subscriber site |

---

## Village Fiber Packages

| Package | Speed | Tenant Pays | Innago Line Item | UISP Rate |
|---------|-------|-------------|------------------|-----------|
| Village Fiber 500 | 500 Mbps | Included with rent | $0 | $45 |
| Village Fiber 1G | 1 Gbps | +$10/mo | $10 | $55 |
| Village Fiber 2G | 2 Gbps | +$15/mo | $15 | $60 |

---

## Integration Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VIC-VIL INTEGRATION SERVICE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     Poll every 5 min      ┌─────────────┐                 │
│  │   INNAGO    │ ◄──────────────────────── │   SYNC      │                 │
│  │  API        │                           │   ENGINE    │                 │
│  └─────────────┘                           └──────┬──────┘                 │
│        │                                          │                        │
│        │  • New leases                            │                        │
│        │  • Maintenance tickets                   ▼                        │
│        │  • Tenant info                   ┌─────────────┐                  │
│        │                                  │   UISP      │                  │
│        │                                  │  10.8.10.10 │                  │
│        ▼                                  └─────────────┘                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │                    WORKFLOWS                                            │
│  ├─────────────────────────────────────────────────────────────────────────┤
│  │                                                                         │
│  │  1. NEW LEASE DETECTED (service start = lease start date)              │
│  │     └─► Create UISP client (name, email, unit)                         │
│  │     └─► Add Village Fiber 500 service                                  │
│  │     └─► Find/create subscriber site for unit                           │
│  │     └─► Rename ONU to apartment number (e.g., "ONU-101")               │
│  │     └─► Link device to subscriber site                                 │
│  │     └─► Add fiber line item to Innago invoice (if upgrade)             │
│  │     └─► Send welcome email to tenant                                   │
│  │                                                                         │
│  │  2. MAINTENANCE TICKET (internet keywords)                              │
│  │     └─► Keywords: "internet", "wifi", "fiber", "slow", "outage"        │
│  │     └─► Create ticket in UISP linked to client                         │
│  │     └─► Sync status updates both directions                            │
│  │                                                                         │
│  │  3. PACKAGE UPGRADE REQUEST                                             │
│  │     └─► Keywords: "upgrade", "1g", "2g", "faster"                      │
│  │     └─► Update service plan in UISP                                    │
│  │     └─► Update Innago invoice line item amount                         │
│  │     └─► Reply to ticket confirming change                              │
│  │                                                                         │
│  └─────────────────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## UISP Site Structure

```
Victorian Village (Parent Site)
    │
    ├── Unit 101 (Subscriber Site)
    │       └── ONU-101 (Device) ─── linked to ─── Tenant Service
    │
    ├── Unit 102 (Subscriber Site)
    │       └── ONU-102 (Device) ─── linked to ─── Tenant Service
    │
    ... (118 units)
```

---

## Welcome Email Template

**Subject:** Your Village Fiber Internet is Ready - Unit [#]

```
Hi [Tenant Name],

Welcome to Victorian Village! Your Village Fiber internet is active starting [lease start date].

Important: A router is not included. You'll need to provide your own WiFi router to connect - just plug it into the fiber jack in your unit. Or pick up our recommended one below:

Recommended Router: TP-Link Archer AX55 - $70
https://www.amazon.com/TP-Link-WiFi-AX3000-Smart-Router/dp/B09G5W9R6R

Note: If you plan on upgrading to Village Fiber 2G, you'll need the Pro model to get full speeds.
https://www.amazon.com/TP-Link-AX3000-Archer-AX55-Pro/dp/B0BTD7V93F

Your Current Plan: Village Fiber 500 (500 Mbps) - Included with rent

Want faster speeds? Submit a maintenance request in your tenant portal with subject "Internet Upgrade" and your choice:

| Package          | Speed    | Add-on   |
|------------------|----------|----------|
| Village Fiber 1G | 1 Gbps   | +$10/mo  |
| Village Fiber 2G | 2 Gbps   | +$15/mo  |

Internet issues? Submit a maintenance request with "Internet" in the subject.

— ERE Fiber LLC
```

---

## Configuration (to be filled in)

```yaml
# config.yaml
innago:
  api_url: https://api-my.innago.com/openapi
  api_key: <PENDING>
  property_id: <PENDING>

uisp:
  host: 10.8.10.10
  crm_api_key: <PENDING>
  nms_api_key: <PENDING>
  parent_site_id: <PENDING>

email:
  from: internet@erefiber.com  # or whatever address
  smtp_host: <PENDING>
  smtp_port: 587
  smtp_user: <PENDING>
  smtp_pass: <PENDING>

packages:
  - name: Village Fiber 500
    speed_down: 500
    speed_up: 500
    base_price: 45
    tenant_addon: 0
    default: true
  - name: Village Fiber 1G
    speed_down: 1000
    speed_up: 1000
    base_price: 55
    tenant_addon: 10
  - name: Village Fiber 2G
    speed_down: 2000
    speed_up: 2000
    base_price: 60
    tenant_addon: 15

polling:
  interval_minutes: 5
```

---

## To Do

- [ ] Get Innago API key
- [ ] Get UISP CRM API key
- [ ] Get UISP NMS API key
- [ ] Set up 118 subscriber sites in UISP (or let integration create them)
- [ ] Create Village Fiber service plans in UISP
- [ ] Build integration service
- [ ] Test with single unit
- [ ] Deploy

---

## Tech Stack (Planned)

- Python 3.x
- SQLite (sync state tracking)
- systemd service or cron for scheduling
