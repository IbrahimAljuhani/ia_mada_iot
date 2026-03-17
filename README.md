# ia_mada_iot — POS Mada Terminal via IoT Box

**Author:** Ibrahim Aljuhani  
**Email:** info@ia.sa  
**Website:** https://ia.sa  
**Version:** 18.0.1.1.0  
**License:** LGPL-3  

---

## Overview

Integrates Mada payment terminals (NeoLeap) with Odoo 18 POS via IoT Box on Raspberry Pi.

Solves the Mixed Content problem: Odoo runs on `https://` but NeoLeap only speaks `ws://IP:7000`.  
The IoT Box acts as a secure bridge — the browser communicates with Odoo over HTTPS, and the Pi connects to NeoLeap locally.

Supports **unlimited Mada terminals** — create one payment method per device, each with its own NeoLeap IP address.

---

## Requirements

| Component | Details |
|-----------|---------|
| Odoo | 18.0 Enterprise |
| Raspberry Pi | **3B, 3B+ or 4 |
| IoT Box image | `iotbox-latest.zip` from nightly.odoo.com |
| NeoLeap Mada | Installed and running on each payment device |
| Network | All devices on the same WiFi/LAN |
| Python library | `websocket-client` installed on Pi 

---

## NeoLeap Protocol

```
IoT Box  →  ws://192.168.1.10:7000
  SEND   {"Command": "CHECK_STATUS"}
  RECV   {"EventName": "TERMINAL_STATUS", "TerminalStatus": "READY"}
  SEND   {"Command": "SALE", "Amount": "150.00", "AdditionalData": "00001-001-0001"}
  RECV   {"EventName": "TERMINAL_RESPONSE", "JsonResult": {"StatusCode": "00", ...}}
```

| StatusCode | Meaning |
|------------|---------|
| `00` | Approved |
| `01` | Declined by bank |
| `11` | Cancelled by customer |

---

## Installation

### Step 1 — Odoo Server

```bash
# Upload ia_mada_iot.zip via WinSCP to /tmp/, then run:

sudo unzip -o /tmp/ia_mada_iot.zip -d /odoo/custom/addons/
sudo chown -R odoo:odoo /odoo/custom/addons/ia_mada_iot

# Add neoleap_ip column to database (first install only)
sudo -u odoo psql -d myodoo -c "
ALTER TABLE pos_payment_method ADD COLUMN IF NOT EXISTS neoleap_ip VARCHAR;
"

# Install the module
sudo -u odoo /odoo/venv/bin/python /odoo/odoo-bin \
  --config=/etc/odoo.conf \
  -d myodoo \
  -i ia_mada_iot \
  --stop-after-init

sudo systemctl restart odoo
```

> Replace `/odoo/`, `myodoo`, and `odoo.conf` with your actual paths.

---

### Step 2 — Raspberry Pi (IoT Box)

```bash
# Flash SD card with iotbox-latest.zip using balenaEtcher
# URL: http://nightly.odoo.com/master/iotbox/iotbox-latest.zip

# After Pi boots and connects to Odoo, install websocket-client:
pip3 install websocket-client --break-system-packages

# Restart IoT service
sudo systemctl restart odoo.service
```

---

### Step 3 — Add Network Printers to CUPS (optional)

SSH into the Pi, then run one command per printer:

```bash
# Printer at 192.168.1.101 on port 9100
/usr/sbin/lpadmin -p socket1921681019100 \
  -v socket://192.168.1.101:9100 \
  -m raw \
  -D "Cashier Printer" \
  -L "POS Counter" \
  -E

# Printer at 192.168.1.102
/usr/sbin/lpadmin -p socket1921681029100 \
  -v socket://192.168.1.102:9100 \
  -m raw \
  -D "Kitchen Printer" \
  -L "Kitchen" \
  -E

# Restart IoT to detect new printers
sudo systemctl restart odoo.service
```

> The printer name must match the socket URL with dots and colons removed.  
> Example: `socket://192.168.1.101:9100` → name: `socket1921681019100`

---

### Step 4 — Odoo Configuration

1. Go to **IoT → IoT Boxes** and confirm the Pi is connected.
2. Go to **POS → Configuration → Payment Methods → New** and create one method per terminal:

| Field | Value |
|-------|-------|
| Name | `Mada - Cashier` |
| Journal | Bank |
| Integration | Terminal |
| Integrate with | Mada Terminal (IoT) |
| NeoLeap IP Address | `192.168.1.10` |

3. Click **Test Connection** to verify the terminal is reachable.
4. Go to **POS → Configuration → Settings** and assign the payment method to each POS.

---

## Multiple Terminals

Create one payment method per device — no limit:

| Payment Method | NeoLeap IP Address | Used In |
|----------------|--------------------|---------|
| Mada - Cashier | 192.168.1.10 | Cashier POS |
| Mada - Drive-through | 192.168.1.11 | Drive-through POS |
| Mada - Terminal 3 | 192.168.1.12 | Any additional POS |

---

## File Structure

```
ia_mada_iot/
├── __manifest__.py
├── __init__.py
├── CHANGELOG.md
├── README.md
├── controllers/
│   ├── __init__.py
│   └── main.py                  ← fixes IoT Box saas~19.1 compatibility
├── models/
│   ├── __init__.py
│   └── pos_payment_method.py    ← adds mada_iot terminal + neoleap_ip field + test button
├── iot_handlers/
│   ├── __init__.py
│   └── mada_handler.py          ← MadaDriver + MadaInterface (runs on Raspberry Pi only)
├── static/src/app/
│   ├── model.js                 ← registers PaymentMada payment method
│   ├── payment_mada.js          ← POS payment logic, bilingual AR/EN messages
│   └── payment_screen.js        ← PaymentScreen patches for mada_iot
└── views/
    └── pos_payment_method_views.xml
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `column neoleap_ip does not exist` | Run: `ALTER TABLE pos_payment_method ADD COLUMN IF NOT EXISTS neoleap_ip VARCHAR;` |
| `External ID not found: view_pos_payment_method_form` | Correct ref is `point_of_sale.pos_payment_method_view_form` |
| `NoneType has no attribute groups` | Remove the `i18n/` folder — `.po` files break Arabic locale loading |
| `500 error on /iot/get_handlers` | Already fixed by `controllers/main.py` override |
| Mada terminal not connected | Verify IoT Box is running and NeoLeap app is open on the terminal device |
| `websocket-client` not installed | Run `pip3 install websocket-client --break-system-packages` on Pi |
| Terminal is busy | NeoLeap is processing another transaction — wait and retry |
| Printer not detected by IoT | Rename CUPS printer to match socket identifier (e.g. `socket1921681019100`) |
| IoT Box shows 0 devices | Restart Pi and wait 3 minutes for handlers to load |
