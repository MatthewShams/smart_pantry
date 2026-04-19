# Smart Pantry 🥫

AI-powered pantry monitor using a Raspberry Pi 4B, webcam, and WS2812B LED strips.

## Features
- **Auto-scan** on door open (magnetic reed switch → GPIO)
- **Claude Vision** identifies ingredients, quantities, and expiry dates
- **Per-slot LEDs** — green=fresh, amber=expiring, red=expired, yellow=recipe needed, blue=scanning
- **Recipe engine** — AI suggests recipes from what you have; LEDs highlight needed ingredients
- **Grocery list** — auto-generated from expired/low stock
- **Web dashboard** — live shelf map, ingredient manager, recipe picker

---

## Hardware wiring

```
┌──────────────────────────────────────────────────────────────┐
│  Raspberry Pi 4B                                             │
│                                                              │
│  GPIO18 (PWM) ──[470Ω]──► WS2812B DATA IN                   │
│  5V          ────────────► WS2812B +5V  (use separate PSU    │
│  GND         ────────────► WS2812B GND   for >30 LEDs)       │
│                                                              │
│  GPIO17      ────────────► Reed switch ──► GND               │
│  3.3V        ──[10kΩ]───► GPIO17  (pull-up — use built-in)  │
│                                                              │
│  USB         ────────────► Webcam                            │
└──────────────────────────────────────────────────────────────┘
```

**LED strip layout** (12 LEDs = 3 rows × 4 cols):
```
 Slot  0  |  1  |  2  |  3       ← top shelf
 Slot  4  |  5  |  6  |  7       ← middle shelf
 Slot  8  |  9  | 10  | 11       ← bottom shelf
```
Each slot = one LED above the shelf position.

**Parts needed:**
| Part | Notes |
|---|---|
| Raspberry Pi 4B | Any RAM variant |
| USB webcam | Wide-angle recommended |
| WS2812B strip | Cut to 12 LEDs, 5V |
| 470Ω resistor | On DATA line |
| 1000μF capacitor | On 5V/GND of strip |
| Magnetic reed switch | Normally-open |
| 5V PSU (≥3A) | For Pi + LEDs |

---

## Setup

### 1. Install dependencies

```bash
# On the Raspberry Pi
sudo apt update
sudo apt install python3-pip python3-venv libopencv-dev -y

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Pi-specific
pip install rpi_ws281x RPi.GPIO
```

### 2. Set API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Run

```bash
# Must run as root for GPIO/LED access on Pi
sudo -E python main.py
```

Then open **http://<pi-ip>:5000** on any device on the same network.

### Dev mode (laptop — no Pi hardware)

```bash
python main.py
# GPIO and LEDs fall back to console mocks automatically
# Trigger scans via the web UI → "Scan now"
```

---

## Project structure

```
smart_pantry/
├── main.py                 # Orchestrator + door-sensor loop
├── config.py               # All tuneable settings
├── requirements.txt
├── camera/
│   └── capture.py          # OpenCV webcam → base64 JPEG
├── vision/
│   └── analyzer.py         # Claude Vision API calls
├── pantry/
│   └── database.py         # SQLite CRUD
├── leds/
│   └── controller.py       # WS2812B / mock LED driver
├── recipes/
│   └── engine.py           # Recipe matching + LED highlight
└── web/
    ├── app.py              # Flask REST API
    └── templates/
        └── index.html      # Single-page dashboard
```

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/ingredients` | List all pantry items |
| POST | `/api/ingredients` | Add/update an ingredient |
| DELETE | `/api/ingredients/<id>` | Remove an ingredient |
| POST | `/api/scan` | Trigger a camera scan |
| GET | `/api/status` | Scanning state + counts |
| GET | `/api/recipes/suggest?dietary=&count=3` | AI recipe suggestions |
| POST | `/api/recipes/highlight` | Light up recipe ingredient LEDs |
| POST | `/api/recipes/clear` | Restore status LEDs |
| GET | `/api/expiring?days=7` | Expiring / expired items |
| GET | `/api/grocery-list` | Auto-generated shopping list |
| POST | `/api/leds/blink` | Blink a specific slot `{"slot": 3}` |
| POST | `/api/leds/clear` | Turn off all LEDs |

---

## Extending

- **Multiple shelves / cameras**: run two `CameraCapture` instances, pass `shelf_offset` so slot IDs don't collide.
- **Barcode scanning**: add `pyzbar` to read barcodes in `capture.py` before sending to Claude — great for exact expiry dates.
- **Mobile push alerts**: add `pushover` or Telegram bot to `grocery/manager.py` when something expires.
- **OLED display**: attach a 128×64 I²C OLED and show current recipe on the pantry door.
