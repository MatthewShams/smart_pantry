import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from pantry.database import init_db, upsert_ingredient

# 1. THE NUCLEAR WIPE: Start with a 100% clean slate
if os.path.exists("pantry.db"):
    os.remove("pantry.db")

init_db()

# 2. Only seed "Extras" (shelf_slot=None) 
# The 6 physical spots (0-5) will be EMPTY and ready for your demo
ingredients = [
    dict(name="olive oil",      category="condiment", quantity=500,  unit="ml",     shelf_slot=None),
    dict(name="soy sauce",      category="condiment", quantity=250,  unit="ml",     shelf_slot=None),
    dict(name="salt",           category="spice",     quantity=500,  unit="g",      shelf_slot=None),
    dict(name="black pepper",   category="spice",     quantity=50,   unit="g",      shelf_slot=None),
    dict(name="garlic",         category="produce",   quantity=1,    unit="bulb",   shelf_slot=None),
]

for item in ingredients:
    upsert_ingredient(**item)

print("--- DEMO READY ---")
print("Database wiped. Physical slots 0-5 are now empty.")
