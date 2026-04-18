"""WS2812B LED strip controller.

Falls back to a console mock automatically on non-Pi environments so you can
develop and test the full stack on a laptop.
"""

import time
from config import (
    LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_BRIGHTNESS,
    LED_INVERT, LED_CHANNEL,
    COLOR_OFF, COLOR_FRESH, COLOR_EXPIRING, COLOR_EXPIRED,
    COLOR_RECIPE_NEEDED, COLOR_SCAN_PULSE, COLOR_MISSING_FROM_PANTRY,
    EXPIRY_WARNING_DAYS,
)

# ── Hardware import with graceful mock ────────────────────────────────────
try:
    from rpi_ws281x import PixelStrip, Color as _Color
    HAS_LEDS = True
    print("[leds] rpi_ws281x loaded — real LED strip active")
except ImportError:
    HAS_LEDS = False
    print("[leds] rpi_ws281x not found — using console mock")

    def _Color(r: int, g: int, b: int) -> int:
        return (int(r) << 16) | (int(g) << 8) | int(b)

    class PixelStrip:  # noqa: N801
        def __init__(self, count, *args, **kwargs):
            self._pixels = [0] * count
        def begin(self): pass
        def setPixelColor(self, n, color): self._pixels[n] = color
        def show(self):
            icons = {0: "⚫"}
            row = []
            for p in self._pixels:
                r, g, b = (p >> 16) & 0xFF, (p >> 8) & 0xFF, p & 0xFF
                if r == 0 and g == 0 and b == 0:
                    row.append("⚫")
                elif g > r and g > b:
                    row.append("🟢")
                elif r > 200 and g > 100 and b == 0:
                    row.append("🟠")
                elif r > 200 and g == 0 and b == 0:
                    row.append("🔴")
                elif r > 200 and g > 180 and b == 0:
                    row.append("🟡")
                elif b > r and b > g:
                    row.append("🔵")
                else:
                    row.append("🟣")
            print("[leds]", " ".join(row))
        def numPixels(self): return len(self._pixels)
        def setBrightness(self, b): pass


# ── Controller ────────────────────────────────────────────────────────────

class LEDController:
    def __init__(self):
        self.strip = PixelStrip(
            LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
            LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL
        )
        self.strip.begin()
        self._state: list[tuple] = [COLOR_OFF] * LED_COUNT  # in-memory mirror

    # ── Low-level primitives ──────────────────────────────────────────────

    def _set(self, slot: int, color: tuple):
        if 0 <= slot < LED_COUNT:
            r, g, b = (int(c) for c in color)
            self.strip.setPixelColor(slot, _Color(r, g, b))
            self._state[slot] = (r, g, b)

    def _commit(self):
        self.strip.show()

    # ── Public API ────────────────────────────────────────────────────────

    def clear_all(self):
        for i in range(LED_COUNT):
            self._set(i, COLOR_OFF)
        self._commit()

    def set_slot(self, slot: int, color: tuple):
        self._set(slot, color)
        self._commit()

    def show_pantry_status(self, ingredients: list[dict]):
        """Colour every slot by expiry status. Call after each scan."""
        from datetime import datetime, timedelta
        today        = datetime.now().date()
        warn_cutoff  = today + timedelta(days=EXPIRY_WARNING_DAYS)

        self.clear_all()
        for item in ingredients:
            slot = item.get("shelf_slot")
            if slot is None:
                continue
            exp = item.get("expiry_date")
            if exp:
                exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
                if exp_date < today:
                    color = COLOR_EXPIRED
                elif exp_date <= warn_cutoff:
                    color = COLOR_EXPIRING
                else:
                    color = COLOR_FRESH
            else:
                color = COLOR_FRESH     # No expiry info → assume fresh
            self._set(slot, color)

        self._commit()

    def highlight_recipe_ingredients(self, available_slots: list[int],
                                     missing_slots: list[int] | None = None):
        """
        Yellow  = ingredient in pantry and needed for this recipe.
        Purple  = ingredient needed but not stocked (slot unknown — skip).
        Everything else = OFF.
        """
        self.clear_all()
        for slot in available_slots:
            self._set(slot, COLOR_RECIPE_NEEDED)
        if missing_slots:
            for slot in missing_slots:
                self._set(slot, COLOR_MISSING_FROM_PANTRY)
        self._commit()

    def scan_pulse(self, duration: float = 2.5):
        """Blue breathing animation while Claude analyses the image."""
        steps = 24
        cycles = 3
        delay  = duration / (cycles * steps * 2)
        for _ in range(cycles):
            for i in range(steps):
                b = int(200 * i / steps)
                for s in range(LED_COUNT):
                    self._set(s, (0, 0, b))
                self._commit()
                time.sleep(delay)
            for i in range(steps, 0, -1):
                b = int(200 * i / steps)
                for s in range(LED_COUNT):
                    self._set(s, (0, 0, b))
                self._commit()
                time.sleep(delay)
        self.clear_all()

    def blink_slot(self, slot: int, color: tuple = COLOR_RECIPE_NEEDED, times: int = 3):
        """Flash a single slot — useful for pointing out an ingredient."""
        for _ in range(times):
            self.set_slot(slot, color)
            time.sleep(0.3)
            self.set_slot(slot, COLOR_OFF)
            time.sleep(0.3)

    @property
    def state(self) -> list[tuple]:
        """Current colour state of every slot (for the web API)."""
        return list(self._state)
