"""Recipe engine — matches pantry against recipes and triggers LED highlights."""

from pantry.database import get_all_ingredients
from vision.analyzer import get_recipe_suggestions
from leds.controller import LEDController


class RecipeEngine:
    def __init__(self, led_controller: LEDController):
        self.leds = led_controller

    # ── Helpers ───────────────────────────────────────────────────────────

    def _slot_map(self) -> dict[str, int]:
        """Return {ingredient_name_lower: shelf_slot} for all stocked items."""
        return {
            item["name"].lower(): item["shelf_slot"]
            for item in get_all_ingredients()
            if item.get("shelf_slot") is not None
        }

    def get_available_names(self) -> list[str]:
        return [item["name"] for item in get_all_ingredients()]

    # ── Recipe suggestions ────────────────────────────────────────────────

    def suggest_recipes(self, dietary_prefs: str = "", count: int = 3) -> dict:
        """Ask Claude for recipes using current pantry contents."""
        names = self.get_available_names()
        if not names:
            return {"recipes": [], "error": "Pantry is empty — scan first"}
        return get_recipe_suggestions(names, dietary_prefs, count)

    # ── Completeness scoring ──────────────────────────────────────────────

    def score_recipe(self, recipe: dict) -> dict:
        """Return completeness % and lists of matched / missing ingredients."""
        available = set(n.lower() for n in self.get_available_names())
        uses      = set(i.lower() for i in recipe.get("uses_ingredients", []))
        missing   = set(i.lower() for i in recipe.get("missing_ingredients", []))

        matched  = uses & available
        total    = len(uses) + len(missing)
        pct      = round(len(matched) / total * 100) if total else 0

        return {
            "completeness_pct": pct,
            "available":        sorted(matched),
            "missing":          sorted(missing),
            "total_ingredients": total,
        }

    # ── LED highlight ─────────────────────────────────────────────────────

    def highlight_recipe(self, recipe: dict) -> dict:
        """
        Light up the LED slots of ingredients required by the recipe.
        Yellow = have it · Purple = don't have it (slot unknown, just logged).
        Returns a summary of which slots lit up.
        """
        slot_map = self._slot_map()

        available_slots = []
        missing_names   = []

        for ingredient in recipe.get("uses_ingredients", []):
            slot = slot_map.get(ingredient.lower())
            if slot is not None:
                available_slots.append(slot)
            # else: in pantry but no slot assigned → still usable, just no LED

        for ingredient in recipe.get("missing_ingredients", []):
            slot = slot_map.get(ingredient.lower())
            if slot is not None:
                available_slots.append(slot)  # present under different name?
            else:
                missing_names.append(ingredient)

        self.leds.highlight_recipe_ingredients(available_slots)

        return {
            "highlighted_slots": available_slots,
            "missing_from_pantry": missing_names,
            "recipe_name": recipe.get("name", ""),
        }

    def clear_highlight(self):
        """Restore status-based LED colours after viewing a recipe."""
        self.leds.show_pantry_status(get_all_ingredients())
