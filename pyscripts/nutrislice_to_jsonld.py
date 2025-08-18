# nutrislice_to_jsonld.py
# Transforms raw Nutrislice JSON dumps into **Schema.org JSON‑LD** menus

"""Aug 2025 rev 2 – richer payload
─────────────────────────────────
Added **all** requested fields:
• `hall` and `meal` – provenance for retrieval filters.
• `dietTags` – raw Nutrislice allergen slugs.
• `servingWeight` (grams) – numeric, fallback oz→g.
• Extra micros in `nutrition`: sodium, fiber, sugar.
• `image` ‑ image URL if present.
• `vendorID` ‑ Nutrislice `synced_id` for join keys.
• Still strips “prep time / cook time”.

The script now infers **hall‑slug** and **meal‑type** from the raw‑file
name pattern `<hall>_<meal>_<date>.json`.
"""

from __future__ import annotations
import json, os, re, ssl, certifi
from pathlib import Path
from datetime import date, timedelta
from typing import Tuple, List
from dotenv import load_dotenv

load_dotenv()
# Get the script's directory and resolve paths relative to NLWeb root
SCRIPT_DIR = Path(__file__).parent
NLWEB_ROOT = SCRIPT_DIR.parent
raw_dir_env = os.getenv("RAW_DIR", str(NLWEB_ROOT / "raw_menus"))
jsonld_dir_env = os.getenv("JSONLD_DIR", str(NLWEB_ROOT / "data" / "jsonld"))
RAW_DIR = Path(raw_dir_env) if Path(raw_dir_env).is_absolute() else NLWEB_ROOT / raw_dir_env
JSONLD_DIR = Path(jsonld_dir_env) if Path(jsonld_dir_env).is_absolute() else NLWEB_ROOT / jsonld_dir_env
JSONLD_DIR.mkdir(parents=True, exist_ok=True)

# ── helpers ────────────────────────────────────────────────────────────────

def slugify(s: str) -> str:
    """Convert string to URL-friendly slug."""
    return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')

def map_diets(tags: List[str]) -> List[str]:
    """Nutrislice tag → Schema.org Diet URI."""
    return [f"https://schema.org/{t}Diet" for t in tags]


def clean_description(text: str) -> str:
    if not text:
        return ""
    for bad in ("prep time", "cook time"):
        text = re.sub(bad, "", text, flags=re.I)
    return " ".join(text.split())


def oz_to_g(oz: float | str) -> float:
    try:
        return round(float(oz) * 28.3495, 1)
    except Exception:
        return None

# ── core transform ─────────────────────────────────────────────────────────

def transform_menu(raw_json: dict, hall_slug: str, meal_type: str) -> List[Tuple[dict, str]]:
    outputs: List[Tuple[dict, str]] = []
    for day in raw_json.get("days", []):
        menu_date: str = day.get("date") or "unknown-date"
        sections_info: dict = day.get("menu_info", {})

        # bucket items by menu/section id
        items_by_section: dict[str, list] = {}
        for itm in day.get("menu_items", []):
            if itm.get("is_section_title"):
                continue
            items_by_section.setdefault(str(itm.get("menu_id")), []).append(itm)

        for menu_id, meta in sections_info.items():
            section_name = meta.get("section_options", {}).get("display_name")
            if not section_name:
                continue
            items = items_by_section.get(menu_id, [])
            if not items:
                continue

            menu_obj = {
                "@context": "https://schema.org",
                "@type": "Menu",
                "name": f"{section_name} – {menu_date}",
                "datePublished": menu_date,
                "hall": hall_slug,
                "meal": meal_type,
                "hasMenuSection": [{
                    "@type": "MenuSection",
                    "name": section_name,
                    "hasMenuItem": []
                }]
            }
            section_items = menu_obj["hasMenuSection"][0]["hasMenuItem"]

            for itm in items:
                food = itm.get("food") or {}
                nut  = food.get("rounded_nutrition_info", {})
                size = food.get("serving_size_info", {})

                # textual serving size
                serving_txt = ""
                if size.get("serving_size_amount"):
                    serving_txt = f"{size['serving_size_amount']} {size.get('serving_size_unit', '').strip()}".strip()

                # Skip station/header rows
                food_name = food.get("name", "").strip()
                if (food_name.lower() == (section_name or "").strip().lower()):
                    continue
                if "customer" in (serving_txt or "").lower():
                    continue

                # numeric grams
                grams = size.get("serving_size_grams") if size else None
                serving_size_unit = size.get("serving_size_unit", "") if size else ""
                if not grams and serving_size_unit and serving_size_unit.lower().startswith("oz"):
                    grams = oz_to_g(size.get("serving_size_amount", 0) if size else 0)

                # diet tags
                tags = [ico.get("slug") or ico.get("synced_name")
                        for ico in food.get("icons", {}).get("food_icons", [])
                        if ico.get("is_filter") or ico.get("is_highlight")]

                # Generate unique URL
                raw_url = (food.get("file_url") or "").strip()
                name_slug = slugify(food_name)
                section_slug = slugify(section_name)
                
                if raw_url:
                    item_url = raw_url
                else:
                    item_url = f"menuitem://{hall_slug}/{meal_type}/{menu_date}/{section_slug}/{name_slug}"

                mi = {
                    "@type": "MenuItem",
                    "name": food_name,
                    "description": clean_description(food.get("description", "")),
                    "url": item_url,
                    "image": food.get("image_url", ""),
                    "servingSize": serving_txt,
                    "vendorID": food.get("synced_id"),
                    "hall": hall_slug,
                    "meal": meal_type,
                    "dietTags": tags,
                    "nutrition": {
                        "@type": "NutritionInformation",
                        "calories": nut.get("calories"),
                        "proteinContent": nut.get("g_protein"),
                        "fatContent": nut.get("g_fat"),
                        "carbohydrateContent": nut.get("g_carbs"),
                        "sodiumContent": nut.get("mg_sodium"),
                        "fiberContent": nut.get("g_fiber"),
                        "sugarContent": nut.get("g_sugar"),
                        "addedSugarContent": nut.get("g_added_sugar")
                    }
                }
                if grams:
                    mi["servingWeight"] = grams
                if tags:
                    mi["suitableForDiet"] = map_diets(tags)

                section_items.append(mi)

            fname = f"{hall_slug}_{meal_type}_{section_name.replace(' ', '_').lower()}_{menu_date}.jsonld"
            outputs.append((menu_obj, fname))

    return outputs

# ── CLI ─────────────────────────────────────────────────────────────────────

def last_sunday(d: date) -> date:
    """Return the Sunday on or before *d* (works whether Sunday is today or earlier in the week)."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


def main():
    # pick the Sunday that fetch_menu.py used when it created the weekly dumps
    sunday_iso = last_sunday(date.today()).isoformat()
        # search recursively because weekly dumps live in dated sub‑folders
    for raw_file in RAW_DIR.rglob(f"*_{sunday_iso}.json"):
        parts = raw_file.stem.split("_")  # <hall>_<meal>_<YYYY-MM-DD>
        if len(parts) < 3:
            continue
        hall_slug, meal_type = parts[0], parts[1]

        raw = json.loads(raw_file.read_text(encoding="utf-8"))
        for menu_obj, fname in transform_menu(raw, hall_slug, meal_type):
            out_path = JSONLD_DIR / fname
            out_path.write_text(json.dumps(menu_obj, ensure_ascii=False, indent=2), encoding="utf-8")
            print("Wrote", out_path)


if __name__ == "__main__":
    main()  # single entrypoint
