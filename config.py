import os

# ── Google Gemini ─────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-1.5-pro"

# ── Camera ────────────────────────────────────────────────────────────────
CAMERA_INDEX       = 0
CAPTURE_RESOLUTION = (1280, 720)
SCAN_COOLDOWN_SEC  = 5

# ── Pantry layout ─────────────────────────────────────────────────────────
NUM_SHELF_SLOTS = 12
SHELF_ROWS      = 3
SHELF_COLS      = 4

# ── LED strip (Pi only, mocked on Windows) ────────────────────────────────
LED_COUNT      = 12
LED_PIN        = 18
LED_FREQ_HZ    = 800_000
LED_DMA        = 10
LED_BRIGHTNESS = 128
LED_INVERT     = False
LED_CHANNEL    = 0

# ── LED colors (R, G, B) ──────────────────────────────────────────────────
COLOR_OFF                 = (0,   0,   0)
COLOR_FRESH               = (0,   220, 80)
COLOR_EXPIRING            = (255, 120, 0)
COLOR_EXPIRED             = (220, 0,   0)
COLOR_RECIPE_NEEDED       = (255, 200, 0)
COLOR_SCAN_PULSE          = (0,   80,  255)
COLOR_MISSING_FROM_PANTRY = (60,  0,   120)

# ── Door sensor (Pi only) ─────────────────────────────────────────────────
DOOR_SENSOR_PIN = 17
DOOR_OPEN_STATE = 0

# ── Database ──────────────────────────────────────────────────────────────
DB_PATH = "pantry.db"

# ── Web server ────────────────────────────────────────────────────────────
WEB_HOST = "0.0.0.0"
WEB_PORT = 5000
DEBUG    = False

# ── Expiry ────────────────────────────────────────────────────────────────
EXPIRY_WARNING_DAYS = 7

# ── Vertex AI ─────────────────────────────────────────────────────────────
GCP_PROJECT_ID = "smartpantry-493703"   # e.g. "smartpantry-123456"
GCP_LOCATION = "us-central1"
