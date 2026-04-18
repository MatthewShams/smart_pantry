"""Vertex AI Gemini via direct API key - no gcloud login needed."""

import json, base64, io, os
import requests
from config import GEMINI_API_KEY

MODEL = "gemini-2.5-flash-lite"
API_URL = f"https://aiplatform.googleapis.com/v1/publishers/google/models/{MODEL}:generateContent"

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

def _call(contents: list) -> str:
    resp = requests.post(
        API_URL,
        headers={"Content-Type": "application/json"},
        params={"key": GEMINI_API_KEY},
        json={"contents": contents,
              "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}}
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

def _parse(text):
    text = text.strip()
    if text.startswith("```"):
        text = text[text.index("\n")+1:]
    if text.endswith("```"):
        text = text[:text.rindex("```")]
    return json.loads(text.strip())

def analyze_pantry_image(image_b64: str) -> dict:
    try:
        contents = [{"role": "user", "parts": [
            {"text": PANTRY_PROMPT},
            {"inlineData": {"mimeType": "image/jpeg", "data": image_b64}}
        ]}]
        return _parse(_call(contents))
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
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        return _parse(_call(contents))
    except Exception as e:
        print(f"[vision] Recipe error: {e}")
        return {"recipes": [], "error": str(e)}
