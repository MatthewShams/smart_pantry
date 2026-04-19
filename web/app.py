"""Flask REST API + web dashboard for Smart Pantry."""

from flask import Flask, jsonify, request, render_template, send_file
from pantry.database import (
    get_all_ingredients, delete_ingredient, upsert_ingredient,
    get_expiring_soon, get_expired,
)


def create_app(pantry_controller) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="../static")
    app.config["JSON_SORT_KEYS"] = False

    # ── Pages ─────────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/static/latest_scan.jpg")
    def latest_scan():
        try:
            return send_file("../static/latest_scan.jpg", mimetype="image/jpeg")
        except FileNotFoundError:
            return "", 404

    # ── Status ────────────────────────────────────────────────────────────

    @app.route("/api/status")
    def status():
        return jsonify({
            "scanning":         pantry_controller.scanning,
            "ingredient_count": len(get_all_ingredients()),
            "expiring_soon":    len(get_expiring_soon()),
            "expired":          len(get_expired()),
            "led_state":        pantry_controller.leds.state,
        })

    # ── Ingredients ───────────────────────────────────────────────────────

    @app.route("/api/ingredients", methods=["GET"])
    def list_ingredients():
        return jsonify(get_all_ingredients())

    @app.route("/api/ingredients", methods=["POST"])
    def add_ingredient():
        d = request.json or {}
        if not d.get("name"):
            return jsonify({"error": "name required"}), 400
        upsert_ingredient(
            name       = d["name"],
            category   = d.get("category"),
            quantity   = d.get("quantity"),
            unit       = d.get("unit"),
            shelf_slot = d.get("shelf_slot"),
            expiry_date= d.get("expiry_date"),
            notes      = d.get("notes"),
        )
        # Refresh LED status
        pantry_controller.leds.show_pantry_status(get_all_ingredients())
        return jsonify({"success": True})

    @app.route("/api/ingredients/<int:ingredient_id>", methods=["DELETE"])
    def remove_ingredient(ingredient_id):
        delete_ingredient(ingredient_id)
        pantry_controller.leds.show_pantry_status(get_all_ingredients())
        return jsonify({"success": True})

    # ── Scan ──────────────────────────────────────────────────────────────

    @app.route("/api/scan", methods=["POST"])
    def trigger_scan():
        """Manually trigger a pantry scan from the web UI."""
        result = pantry_controller.scan_pantry()
        return jsonify(result)

    # ── Recipes ───────────────────────────────────────────────────────────

    @app.route("/api/recipes/suggest", methods=["GET"])
    def suggest():
        prefs = request.args.get("dietary", "")
        count = int(request.args.get("count", 3))
        return jsonify(pantry_controller.recipe_engine.suggest_recipes(prefs, count))

    @app.route("/api/recipes/highlight", methods=["POST"])
    def highlight_recipe():
        recipe = request.json or {}
        return jsonify(pantry_controller.recipe_engine.highlight_recipe(recipe))

    @app.route("/api/recipes/score", methods=["POST"])
    def score_recipe():
        recipe = request.json or {}
        return jsonify(pantry_controller.recipe_engine.score_recipe(recipe))

    @app.route("/api/recipes/clear", methods=["POST"])
    def clear_highlight():
        pantry_controller.recipe_engine.clear_highlight()
        return jsonify({"success": True})

    # ── LEDs ──────────────────────────────────────────────────────────────

    @app.route("/api/leds/clear", methods=["POST"])
    def clear_leds():
        pantry_controller.leds.clear_all()
        return jsonify({"success": True})

    @app.route("/api/leds/status", methods=["POST"])
    def refresh_led_status():
        pantry_controller.leds.show_pantry_status(get_all_ingredients())
        return jsonify({"success": True})

    @app.route("/api/leds/blink", methods=["POST"])
    def blink_slot():
        slot  = request.json.get("slot", 0)
        pantry_controller.leds.blink_slot(slot)
        return jsonify({"success": True})

    # ── Grocery / expiry ──────────────────────────────────────────────────

    @app.route("/api/expiring")
    def expiring():
        days = int(request.args.get("days", 7))
        return jsonify({
            "expiring_soon": get_expiring_soon(days),
            "expired":       get_expired(),
        })

    @app.route("/api/grocery-list")
    def grocery_list():
        expired  = [{"name": i["name"], "reason": "expired",       "priority": "high"}   for i in get_expired()]
        expiring = [{"name": i["name"], "reason": "expiring soon", "priority": "medium"}  for i in get_expiring_soon()]
        return jsonify({"grocery_list": expired + expiring})

    return app
