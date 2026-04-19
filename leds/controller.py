import requests
import time
from config import (
    LED_COUNT, COLOR_OFF, COLOR_FRESH, COLOR_EXPIRING, COLOR_EXPIRED,
    COLOR_RECIPE_NEEDED, COLOR_MISSING_FROM_PANTRY, EXPIRY_WARNING_DAYS
)

ESP32_URL = "http://10.10.11.212"

class LEDController:
    def __init__(self):
        print(f"[leds] Routing LED commands to ESP32 at {ESP32_URL}")
        self._state = [COLOR_OFF] * LED_COUNT
        self.clear_all()

    def _send_colors(self):
        try:
            requests.post(f"{ESP32_URL}/leds", json={"colors": self._state}, timeout=2)
        except Exception as e:
            print(f"[leds] ESP32 connection error: {e}")

    def clear_all(self):
        self._state = [COLOR_OFF] * LED_COUNT
        try:
            requests.post(f"{ESP32_URL}/clear", timeout=2)
        except Exception as e:
            print(f"[leds] ESP32 clear error: {e}")

    def set_slot(self, slot: int, color: tuple):
        if 0 <= slot < LED_COUNT:
            self._state[slot] = color
            self._send_colors()

    def show_pantry_status(self, ingredients: list[dict]):
        from datetime import datetime, timedelta
        today = datetime.now().date()
        warn_cutoff = today + timedelta(days=EXPIRY_WARNING_DAYS)

        self._state = [COLOR_OFF] * LED_COUNT
        for item in ingredients:
            slot = item.get("shelf_slot")
            if slot is None or not (0 <= slot < LED_COUNT):
                continue
            exp = item.get("expiry_date")
            if exp:
                exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
                if exp_date < today:
                    self._state[slot] = COLOR_EXPIRED
                elif exp_date <= warn_cutoff:
                    self._state[slot] = COLOR_EXPIRING
                else:
                    self._state[slot] = COLOR_FRESH
            else:
                self._state[slot] = COLOR_FRESH
        self._send_colors()

    def highlight_recipe_ingredients(self, available_slots: list[int], missing_slots: list[int] | None = None):
        self._state = [COLOR_OFF] * LED_COUNT
        for slot in available_slots:
            if 0 <= slot < LED_COUNT:
                self._state[slot] = COLOR_RECIPE_NEEDED
        if missing_slots:
            for slot in missing_slots:
                if 0 <= slot < LED_COUNT:
                    self._state[slot] = COLOR_MISSING_FROM_PANTRY
        self._send_colors()

    def scan_pulse(self, duration: float = 2.5):
        try:
            requests.post(f"{ESP32_URL}/pulse", timeout=2)
        except Exception as e:
            print(f"[leds] ESP32 pulse error: {e}")

    def blink_slot(self, slot: int, color: tuple = COLOR_RECIPE_NEEDED, times: int = 3):
        original = self._state[slot]
        for _ in range(times):
            self.set_slot(slot, color)
            time.sleep(0.3)
            self.set_slot(slot, COLOR_OFF)
            time.sleep(0.3)
        self.set_slot(slot, original)

    @property
    def state(self) -> list[tuple]:
        return list(self._state)
