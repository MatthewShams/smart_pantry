"""Vertex AI Gemini integration - uses GCP credits directly."""

import json, base64, io
import PIL.Image
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Image as VertexImage
from config import GCP_PROJECT_ID, GCP_LOCATION

vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
model = GenerativeModel("gemini-2.0-flash")

PANTRY_PROMPT = """You are an AI vision module in a smart pantry system.
Analyze the shelf/pantry image and identify every visible food item.

For each item return:
  name        - common name (e.g. "olive oil", "brown rice")
  category    - produce | dairy | grains | protein | condiment | beverage | snack | spice | other
  quantity    - numeric estimate or null
  unit        - pieces | g | kg | ml | L | cup | null
  shelf_slot  - integer 0-based position (0=top-left, left to right, top to bottom)
  expiry_date - "YYYY-MM-DD" if visible, else null
  notes       - brief observation or null

Return ONLY valid JSON, no markdown, no explanation:
{
  "ingredients": [
    {"name":"string","category":"string","quantity":null,"unit":null,"shelf_slot":0,"expiry_date":null,"notes":null}
  ],
  "scan_notes": "one sentence summary"
}"""

RECIPE_PROMPT = """You are a smart pantry chef assistant.
Available ingredients: {ingredients}
{dietary}
Suggest {count} recipes using mostly pantry items.
Return ONLY valid JSON, no markdown:
{{
  "recipes": [
    {{
      "name": "string",
      "uses_ingredients": ["..."],
      "missing_ingredients": ["..."],
      "prep_time_minutes": 30,
      "difficulty": "easy",
      "instructions": "1. Step one\\n2. Step two",
      "tags": ["quick","vegetarian"]
    }}
  ]
}}"""

def _parse(text):
    text = text.strip()
    if text.startswith("```"):
        text = text[text.index("\n")+1:]
    if text.endswith("```"):
        text = text[:text.rindex("```")]
    return json.loads(text.strip())

def analyze_pantry_image(image_b64: str) -> dict:
    try:
        raw  = base64.b64decode(image_b64)
        img  = Part.from_image(VertexImage.from_bytes(raw))
        resp = model.generate_content([PANTRY_PROMPT, img])
        return _parse(resp.text)
    except json.JSONDecodeError as e:
        print(f"[vision] JSON error: {e}")
        return {"ingredients": [], "scan_notes": f"Parse error: {e}"}
    except Exception as e:
        print(f"[vision] Error: {e}")
        return {"ingredients": [], "scan_notes": str(e)}

def get_recipe_suggestions(ingredient_names: list, dietary_prefs: str = "", count: int = 3) -> dict:
    if not ingredient_names:
        return {"recipes": [], "error": "No ingredients in pantry"}
    prompt = RECIPE_PROMPT.format(
        ingredients=", ".join(ingredient_names),
        dietary=f"Dietary preferences: {dietary_prefs}" if dietary_prefs else "",
        count=count
    )
    try:
        resp = model.generate_content(prompt)
        return _parse(resp.text)
    except Exception as e:
        print(f"[vision] Recipe error: {e}")
        return {"recipes": [], "error": str(e)}
