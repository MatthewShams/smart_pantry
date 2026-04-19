import subprocess, requests, json

PROJECT_ID = "smartpantry-493703"
LOCATION   = "us-central1"
MODEL      = "gemini-2.5-flash-lite"

SCAN_PROMPT = """You are a smart pantry vision module.
Analyze this 3-row × 2-column shelf (6 slots, numbered 0-5 left-to-right, top-to-bottom).
Identify every visible food/drink item.

Rules:
- One entry per unique product. If you see duplicates of the same item, set quantity accordingly.
- Ignore non-food objects (bags, packaging without contents, etc.).
- Use specific names ("Diet Coke", not "soda can").

Return ONLY valid JSON with no markdown fences:
{
  "ingredients": [
    {
      "name": "string",
      "category": "produce|dairy|grains|protein|condiment|beverage|snack|spice|other",
      "quantity": 1,
      "unit": "pieces|g|kg|ml|L|can|bottle|null",
      "shelf_slot": 0,
      "expiry_date": "YYYY-MM-DD or null",
      "notes": "string or null"
    }
  ],
  "scan_notes": "one-sentence summary"
}"""

RECIPE_PROMPT = """You are a smart pantry chef assistant.
Available ingredients: {ingredients}
{dietary}
Suggest {count} recipes using mostly pantry items.

Return ONLY valid JSON with no markdown fences:
{{
  "recipes": [
    {{
      "name": "string",
      "uses_ingredients": ["..."],
      "missing_ingredients": ["..."],
      "prep_time_minutes": 30,
      "difficulty": "easy|medium|hard",
      "instructions": "1. Step one\\n2. Step two",
      "tags": ["quick", "vegetarian"]
    }}
  ]
}}"""


def _token():
    return subprocess.check_output(
        ["gcloud", "auth", "print-access-token"]
    ).decode("ascii").strip()


def _url():
    return (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}"
        f"/locations/{LOCATION}/publishers/google/models/{MODEL}:generateContent"
    )


def _parse(text):
    text = text.strip()
    if text.startswith("```"):
        text = text[text.index("\n") + 1:]
    if text.endswith("```"):
        text = text[:text.rindex("```")]
    return json.loads(text.strip())


def analyze_pantry_image(image_b64: str) -> dict:
    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": SCAN_PROMPT},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
            ],
        }]
    }
    try:
        res      = requests.post(_url(), headers={"Authorization": f"Bearer {_token()}"}, json=payload, timeout=30)
        res.raise_for_status()
        raw_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _parse(raw_text)
    except json.JSONDecodeError as e:
        print(f"[vision] JSON parse error: {e}")
        return {"ingredients": [], "scan_notes": f"Parse error: {e}"}
    except Exception as e:
        print(f"[vision] Error: {e}")
        return {"ingredients": [], "scan_notes": str(e)}


def get_recipe_suggestions(ingredient_names: list, dietary_prefs: str = "", count: int = 3) -> dict:
    if not ingredient_names:
        return {"recipes": [], "error": "Pantry is empty — scan first"}
    prompt = RECIPE_PROMPT.format(
        ingredients = ", ".join(ingredient_names),
        dietary     = f"Dietary preferences: {dietary_prefs}" if dietary_prefs else "",
        count       = count,
    )
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    try:
        res      = requests.post(_url(), headers={"Authorization": f"Bearer {_token()}"}, json=payload, timeout=30)
        res.raise_for_status()
        raw_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _parse(raw_text)
    except json.JSONDecodeError as e:
        print(f"[vision] Recipe JSON parse error: {e}")
        return {"recipes": [], "error": f"Parse error: {e}"}
    except Exception as e:
        print(f"[vision] Recipe error: {e}")
        return {"recipes": [], "error": str(e)}
