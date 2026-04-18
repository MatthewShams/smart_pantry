"""Seed the pantry database with realistic ingredients for demo/testing."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from pantry.database import init_db, upsert_ingredient
from datetime import datetime, timedelta

def d(days_from_now):
    return (datetime.now() + timedelta(days=days_from_now)).strftime("%Y-%m-%d")

init_db()

ingredients = [
    # slot 0-3: top shelf — grains & dry goods
    dict(name="pasta",          category="grains",    quantity=500,  unit="g",      shelf_slot=0,  expiry_date=d(365),  notes="spaghetti"),
    dict(name="brown rice",     category="grains",    quantity=1,    unit="kg",     shelf_slot=1,  expiry_date=d(400)),
    dict(name="rolled oats",    category="grains",    quantity=500,  unit="g",      shelf_slot=2,  expiry_date=d(180)),
    dict(name="all-purpose flour", category="grains", quantity=1,    unit="kg",     shelf_slot=3,  expiry_date=d(300)),

    # slot 4-7: middle shelf — condiments, canned, spices
    dict(name="olive oil",      category="condiment", quantity=500,  unit="ml",     shelf_slot=4,  expiry_date=d(500)),
    dict(name="soy sauce",      category="condiment", quantity=250,  unit="ml",     shelf_slot=5,  expiry_date=d(365)),
    dict(name="canned tomatoes",category="produce",   quantity=400,  unit="g",      shelf_slot=6,  expiry_date=d(730)),
    dict(name="black beans",    category="protein",   quantity=400,  unit="g",      shelf_slot=7,  expiry_date=d(700), notes="canned"),

    # slot 8-11: bottom shelf — fresh produce & dairy
    dict(name="eggs",           category="protein",   quantity=6,    unit="pieces", shelf_slot=8,  expiry_date=d(14)),
    dict(name="milk",           category="dairy",     quantity=1,    unit="L",      shelf_slot=9,  expiry_date=d(5),   notes="almost done"),
    dict(name="cheddar cheese", category="dairy",     quantity=200,  unit="g",      shelf_slot=10, expiry_date=d(3),   notes="expiring soon!"),
    dict(name="butter",         category="dairy",     quantity=250,  unit="g",      shelf_slot=11, expiry_date=d(60)),

    # no slot — extras in the pantry
    dict(name="garlic",         category="produce",   quantity=1,    unit="bulb",   shelf_slot=None),
    dict(name="onions",         category="produce",   quantity=3,    unit="pieces", shelf_slot=None),
    dict(name="potatoes",       category="produce",   quantity=5,    unit="pieces", shelf_slot=None),
    dict(name="tomatoes",       category="produce",   quantity=4,    unit="pieces", shelf_slot=None, expiry_date=d(4)),
    dict(name="lemons",         category="produce",   quantity=3,    unit="pieces", shelf_slot=None),
    dict(name="peanut butter",  category="condiment", quantity=400,  unit="g",      shelf_slot=None, expiry_date=d(200)),
    dict(name="honey",          category="condiment", quantity=350,  unit="g",      shelf_slot=None, expiry_date=d(1000)),
    dict(name="salt",           category="spice",     quantity=500,  unit="g",      shelf_slot=None),
    dict(name="black pepper",   category="spice",     quantity=50,   unit="g",      shelf_slot=None),
    dict(name="cumin",          category="spice",     quantity=30,   unit="g",      shelf_slot=None),
    dict(name="paprika",        category="spice",     quantity=30,   unit="g",      shelf_slot=None),
    dict(name="oregano",        category="spice",     quantity=15,   unit="g",      shelf_slot=None),
    dict(name="canned tuna",    category="protein",   quantity=2,    unit="pieces", shelf_slot=None, expiry_date=d(500)),
    dict(name="chicken stock",  category="condiment", quantity=500,  unit="ml",     shelf_slot=None, expiry_date=d(180)),
]

for item in ingredients:
    upsert_ingredient(**item)

print(f"Seeded {len(ingredients)} ingredients into pantry.db")
print("\nSlot map (what the LEDs will show):")
print("  Top row:    [pasta] [brown rice] [oats] [flour]")
print("  Middle row: [olive oil] [soy sauce] [canned tomatoes] [black beans]")
print("  Bottom row: [eggs] [milk] [cheddar*] [butter]")
print("\n* cheddar and milk are expiring soon — LEDs will show amber/red")
