#!/usr/bin/env python3
"""Smart Pantry - main entry point. Runs on Windows (mocked hardware) and Pi (real hardware)."""

import threading, time, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from config import WEB_HOST, WEB_PORT, SCAN_COOLDOWN_SEC
from pantry.database import init_db, upsert_ingredient, get_all_ingredients, log_scan
from leds.controller import LEDController
from recipes.engine import RecipeEngine

# Camera — optional, skip gracefully if no webcam
try:
    from camera.capture import CameraCapture
    HAS_CAMERA = True
except Exception:
    HAS_CAMERA = False

# Vision
from vision.analyzer import analyze_pantry_image

# GPIO — Pi only
try:
    import RPi.GPIO as GPIO
    from config import DOOR_SENSOR_PIN
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

os.makedirs("static", exist_ok=True)


class SmartPantry:
    def __init__(self):
        print("─" * 45)
        print("  Smart Pantry  |  starting up…")
        print("─" * 45)
        init_db()
        self.leds          = LEDController()
        self.recipe_engine = RecipeEngine(self.leds)
        self.camera        = CameraCapture() if HAS_CAMERA else None
        self.scanning      = False
        self._running      = True
        self._last_scan    = 0.0

        if HAS_GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(DOOR_SENSOR_PIN, GPIO.FALLING,
                                  callback=self._door_opened, bouncetime=2000)
            print(f"Door sensor on GPIO{DOOR_SENSOR_PIN}")

    def start(self):
        if self.camera:
            self.camera.open()

        ingredients = get_all_ingredients()
        if ingredients:
            self.leds.show_pantry_status(ingredients)
            print(f"Loaded {len(ingredients)} ingredients from database")
        else:
            print("Pantry is empty — run seed.py or trigger a scan")

        from web.app import create_app
        app = create_app(self)
        t = threading.Thread(
            target=lambda: app.run(host=WEB_HOST, port=WEB_PORT,
                                   debug=False, use_reloader=False),
            daemon=True
        )
        t.start()
        print(f"\nDashboard ready → http://localhost:{WEB_PORT}")
        print("Press Ctrl-C to stop\n")

        try:
            while self._running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        self._running = False
        self.leds.clear_all()
        if self.camera:
            self.camera.close()
        if HAS_GPIO:
            GPIO.cleanup()
        print("Stopped.")

    def _door_opened(self, _):
        if not self.scanning and time.time() - self._last_scan > SCAN_COOLDOWN_SEC:
            threading.Thread(target=self.scan_pantry, daemon=True).start()

    def scan_pantry(self) -> dict:
        if self.scanning:
            return {"error": "Already scanning"}
        if not self.camera:
            return {"error": "No camera available on this machine"}

        self.scanning = True
        try:
            threading.Thread(target=self.leds.scan_pulse, daemon=True).start()
            print("Capturing frame…")
            b64 = self.camera.capture_frame()
            self.camera.capture_to_file("static/latest_scan.jpg")

            print("Sending to Gemini Vision…")
            result = analyze_pantry_image(b64)
            items  = result.get("ingredients", [])
            print(f"Detected {len(items)} items — {result.get('scan_notes','')}")

            for item in items:
                upsert_ingredient(
                    name=item["name"], category=item.get("category"),
                    quantity=item.get("quantity"), unit=item.get("unit"),
                    shelf_slot=item.get("shelf_slot"),
                    expiry_date=item.get("expiry_date"), notes=item.get("notes")
                )

            log_scan(str(result), len(items))
            self.leds.show_pantry_status(get_all_ingredients())
            self._last_scan = time.time()
            return {"success": True, "items_detected": len(items), "data": result}

        except Exception as e:
            print(f"Scan error: {e}")
            self.leds.clear_all()
            return {"error": str(e)}
        finally:
            self.scanning = False


if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY not set — vision and recipes won't work")
        print("Set it with:  $env:GEMINI_API_KEY='AIza...'  (PowerShell)\n")
    SmartPantry().start()
