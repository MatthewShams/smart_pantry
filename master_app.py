import json, time, base64, requests, os, subprocess
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template, send_file
from vision.analyzer import analyze_pantry_image, get_recipe_suggestions
from pantry.database import (
    get_all_ingredients, upsert_ingredient, delete_ingredient,
    get_expiring_soon, get_expired, log_scan,
)

base_dir    = os.path.abspath(os.path.dirname(__file__))
static_dir  = os.path.join(base_dir, "static")
template_dir = os.path.join(base_dir, "templates")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

ESP32_IP         = "10.10.11.212"
LATEST_IMAGE     = os.path.join(static_dir, "latest_scan.jpg")
EXPIRY_WARN_DAYS = 7
# Each shelf slot maps to a contiguous run of WS2812B LEDs (50 total, 6 slots)
LED_MAP = [[0, 7], [8, 15], [16, 23], [24, 31], [32, 39], [40, 49]]

STATE = {"scanning": False}


# ── LED helpers ───────────────────────────────────────────────────────────────

def _slot_colors(ingredients):
    """Return a 50-element color list reflecting ingredient expiry states."""
    today       = datetime.now().date()
    warn_cutoff = today + timedelta(days=EXPIRY_WARN_DAYS)
    slot_color  = {i: [0, 0, 0] for i in range(6)}

    for item in ingredients:
        slot = item.get("shelf_slot")
        if slot is None or not (0 <= slot < 6):
            continue
        exp = item.get("expiry_date")
        if exp:
            try:
                exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
                if exp_date < today:
                    slot_color[slot] = [220, 0, 0]    # expired  → red
                elif exp_date <= warn_cutoff:
                    slot_color[slot] = [255, 120, 0]  # expiring → orange
                else:
                    slot_color[slot] = [0, 220, 80]   # fresh    → green
            except ValueError:
                slot_color[slot] = [0, 220, 80]
        else:
            slot_color[slot] = [0, 220, 80]

    colors = [[0, 0, 0]] * 50
    for slot, (start, end) in enumerate(LED_MAP):
        c = slot_color[slot]
        for i in range(start, end + 1):
            colors[i] = c
    return colors


def _push_leds(colors):
    try:
        requests.post(f"http://{ESP32_IP}/leds", json={"colors": colors}, timeout=2)
    except Exception as e:
        print(f"[leds] ESP32 unreachable: {e}")


def _refresh_leds():
    _push_leds(_slot_colors(get_all_ingredients()))


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/static/latest_scan.jpg")
def latest_scan_img():
    try:
        return send_file(LATEST_IMAGE, mimetype="image/jpeg")
    except FileNotFoundError:
        return "", 404


# ── Status ────────────────────────────────────────────────────────────────────

@app.route("/api/status")
def status():
    return jsonify({
        "scanning":         STATE["scanning"],
        "ingredient_count": len(get_all_ingredients()),
        "expiring_soon":    len(get_expiring_soon()),
        "expired":          len(get_expired()),
        "led_state":        "active",
    })


# ── Ingredients ───────────────────────────────────────────────────────────────

@app.route("/api/ingredients", methods=["GET"])
def list_ingredients():
    return jsonify(get_all_ingredients())


@app.route("/api/ingredients", methods=["POST"])
def add_ingredient():
    d = request.json or {}
    if not d.get("name"):
        return jsonify({"error": "name required"}), 400
    upsert_ingredient(
        name        = d["name"],
        category    = d.get("category"),
        quantity    = d.get("quantity"),
        unit        = d.get("unit"),
        shelf_slot  = d.get("shelf_slot"),
        expiry_date = d.get("expiry_date"),
        notes       = d.get("notes"),
    )
    _refresh_leds()
    return jsonify({"success": True})


@app.route("/api/ingredients/<int:ing_id>", methods=["DELETE"])
def delete_ing(ing_id):
    delete_ingredient(ing_id)
    _refresh_leds()
    return jsonify({"success": True})


# ── Scan ──────────────────────────────────────────────────────────────────────

def _do_scan():
    os.makedirs(static_dir, exist_ok=True)
    cmd = (
        f"timeout --signal=SIGINT 5s gst-launch-1.0 qtiqmmfsrc "
        f"! video/x-raw,format=NV12,width=1280,height=720 "
        f"! videoconvert ! jpegenc "
        f"! multifilesink location={LATEST_IMAGE} max-files=1"
    )
    subprocess.run(cmd, shell=True)
    if not os.path.exists(LATEST_IMAGE):
        raise RuntimeError("Camera failed to save image")

    with open(LATEST_IMAGE, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    result = analyze_pantry_image(b64)
    items  = result.get("ingredients", [])
    log_scan(json.dumps(result), len(items))

    for item in items:
        upsert_ingredient(
            name        = item["name"],
            category    = item.get("category"),
            quantity    = item.get("quantity"),
            unit        = item.get("unit"),
            shelf_slot  = item.get("shelf_slot"),
            expiry_date = item.get("expiry_date"),
            notes       = item.get("notes"),
        )

    _refresh_leds()
    return {"success": True, "items_detected": len(items), "data": result}


@app.route("/scan", methods=["POST"])       # ESP32 door-open trigger
@app.route("/api/scan", methods=["POST"])   # web UI / manual
def run_scan():
    if STATE["scanning"]:
        return jsonify({"error": "Already scanning"}), 400
    STATE["scanning"] = True
    try:
        return jsonify(_do_scan())
    except Exception as e:
        print(f"[scan] Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        STATE["scanning"] = False


# ── Recipes ───────────────────────────────────────────────────────────────────

@app.route("/api/recipes/suggest", methods=["GET"])
def suggest_recipes():
    names = [i["name"] for i in get_all_ingredients() if i.get("name")]
    if not names:
        return jsonify({"recipes": [], "error": "Pantry is empty — scan first"})
    prefs  = request.args.get("dietary", "")
    count  = int(request.args.get("count", 3))
    result = get_recipe_suggestions(names, prefs, count)
    return jsonify(result if "recipes" in result else {"recipes": []})


@app.route("/api/recipes/highlight", methods=["POST"])
def highlight_recipe():
    recipe   = request.json or {}
    all_ings = get_all_ingredients()
    slot_map = {i["name"].lower(): i["shelf_slot"] for i in all_ings if i.get("shelf_slot") is not None}

    colors = [[0, 0, 0]] * 50
    highlighted = []
    for name in recipe.get("uses_ingredients", []):
        slot = slot_map.get(name.lower())
        if slot is not None and 0 <= slot < 6:
            start, end = LED_MAP[slot]
            for i in range(start, end + 1):
                colors[i] = [255, 200, 0]   # amber = recipe ingredient
            highlighted.append(slot)

    _push_leds(colors)
    return jsonify({"highlighted_slots": highlighted})


@app.route("/api/recipes/clear", methods=["POST"])
def clear_highlight():
    _refresh_leds()
    return jsonify({"success": True})


@app.route("/api/recipes/score", methods=["POST"])
def score_recipe():
    recipe    = request.json or {}
    available = {i["name"].lower() for i in get_all_ingredients()}
    uses      = {n.lower() for n in recipe.get("uses_ingredients", [])}
    missing   = {n.lower() for n in recipe.get("missing_ingredients", [])}
    matched   = uses & available
    total     = len(uses) + len(missing)
    pct       = round(len(matched) / total * 100) if total else 0
    return jsonify({
        "completeness_pct": pct,
        "available":        sorted(matched),
        "missing":          sorted(missing),
    })


# ── LEDs ──────────────────────────────────────────────────────────────────────

@app.route("/api/leds/clear", methods=["POST"])
def clear_leds():
    _push_leds([[0, 0, 0]] * 50)
    return jsonify({"success": True})


@app.route("/api/leds/status", methods=["POST"])
def refresh_led_status():
    _refresh_leds()
    return jsonify({"success": True})


@app.route("/api/leds/blink", methods=["POST"])
def blink_slot():
    slot = (request.json or {}).get("slot", 0)
    if not (0 <= slot < 6):
        return jsonify({"error": "invalid slot"}), 400
    start, end = LED_MAP[slot]
    for _ in range(3):
        on = [[0, 0, 0]] * 50
        for i in range(start, end + 1):
            on[i] = [255, 200, 0]
        _push_leds(on)
        time.sleep(0.3)
        _push_leds([[0, 0, 0]] * 50)
        time.sleep(0.3)
    _refresh_leds()
    return jsonify({"success": True})


# ── Grocery / expiry ──────────────────────────────────────────────────────────

@app.route("/api/grocery-list")
def grocery_list():
    expired  = [{"name": i["name"], "reason": "expired",       "priority": "high"}   for i in get_expired()]
    expiring = [{"name": i["name"], "reason": "expiring soon", "priority": "medium"}  for i in get_expiring_soon()]
    return jsonify({"grocery_list": expired + expiring})


@app.route("/api/expiring")
def expiring():
    days = int(request.args.get("days", 7))
    return jsonify({"expiring_soon": get_expiring_soon(days), "expired": get_expired()})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(static_dir, exist_ok=True)
    print("Smart Pantry starting on port 5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
