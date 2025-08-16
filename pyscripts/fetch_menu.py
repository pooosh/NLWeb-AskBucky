# fetch_menu.py
"""Download one week of Nutrislice menus for every hall / meal listed in .env.

Folders created:
    raw_menus/2025-08-03/four-lakes-market_lunch_2025-08-03.json
"""
import os, asyncio, aiohttp, json
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv

# ── Config from .env ──────────────────────────────────────────────────────────
load_dotenv()

BASE_URL       = os.getenv("NUTRISLICE_API_URL", "").rstrip("/")
HALLS          = [s.strip() for s in os.getenv("DINING_HALL_SLUGS", "").split(",") if s.strip()]
MEALS          = [s.strip() for s in os.getenv("MEAL_TYPES", "").split(",") if s.strip()]
RAW_ROOT       = Path(os.getenv("RAW_DIR", "raw_menus"))

if not (BASE_URL and HALLS and MEALS):
    raise RuntimeError("Check .env — NUTRISLICE_API_URL, DINING_HALL_SLUGS and MEAL_TYPES are required")

# ── Helper: start-of-week (Sunday) folder name ───────────────────────────────
today   = date.today()
sunday  = today - timedelta(days=(today.weekday()+1) % 7)   # 0=Mon … 6=Sun
folder  = RAW_ROOT / sunday.isoformat()                     # e.g. raw_menus/2025-08-03
folder.mkdir(parents=True, exist_ok=True)

def api_url(slug: str, meal: str, d: date) -> str:
    """Build Nutrislice weekly-menu URL."""
    return (f"{BASE_URL}/menu/api/weeks/school/{slug}"
            f"/menu-type/{meal}/{d.year}/{d.month:02d}/{d.day:02d}/")

# ── Async fetch --------------------------------------------------------------
async def fetch(session, slug, meal):
    url = api_url(slug, meal, sunday)

    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"• closed {slug} {meal} (HTTP {resp.status})")
                return

            data = await resp.json()  # parse once

            # 1️⃣ empty days or all menu_items empty -> closed
            def menu_is_empty(d):
                for day in d.get("days", []):
                    for itm in day.get("menu_items", []):
                        if itm.get("food"):        # has real food item
                            return False
                return True

            if menu_is_empty(data):
                print(f"• closed {slug} {meal} (no menu items)")
                return

            # 2️⃣ Nutrislice fallback to another hall
            if data.get("school_slug") and data["school_slug"] != slug:
                print(f"• closed {slug} {meal} (API returned {data['school_slug']})")
                return

            # ✅ hall is open – save raw JSON
            out = folder / f"{slug}_{meal}_{sunday}.json"
            out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            print(f"✓ {out.relative_to(RAW_ROOT)}")

    except Exception as e:
        print(f"• error {slug} {meal}: {e}")
        
async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, h, m) for h in HALLS for m in MEALS]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
