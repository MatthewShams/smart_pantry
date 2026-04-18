"""Test Vertex AI Gemini connection."""
import sys, os, argparse, base64
sys.path.insert(0, os.path.dirname(__file__))

def test_text():
    print("\n── Test 1: Recipe suggestions ──")
    from vision.analyzer import get_recipe_suggestions
    result = get_recipe_suggestions(
        ["pasta", "eggs", "cheddar cheese", "butter", "garlic", "black pepper"],
        count=2
    )
    if "error" in result:
        print(f"FAILED: {result['error']}")
        return False
    for r in result.get("recipes", []):
        print(f"  {r['name']} ({r['difficulty']}, {r['prep_time_minutes']} min)")
        print(f"    Uses: {', '.join(r['uses_ingredients'])}")
    print("PASSED")
    return True

def test_vision(image_path):
    print(f"\n── Test 2: Vision on {image_path} ──")
    from vision.analyzer import analyze_pantry_image
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    result = analyze_pantry_image(b64)
    items = result.get("ingredients", [])
    print(f"Detected {len(items)} items:")
    for item in items:
        print(f"  [{item['shelf_slot']}] {item['name']}")
    print("PASSED" if items else "WARNING: no items detected")
    return bool(items)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="Path to a shelf photo")
    args = parser.parse_args()

    print("=== Vertex AI Gemini Test ===")
    ok = test_text()

    if args.image:
        test_vision(args.image)
    else:
        print("\n── Test 2: Vision (skipped — no --image provided) ──")

    print("\n=== Done ===")
    print("Vertex AI is working! Run: python main.py" if ok else "Something failed.")