#!/usr/bin/env python3
"""
Delete ALL JSON-LD files from the previous week (Sun..Sat).

- Figures out last Sunday's date (relative to 'today') and deletes files
  ending with _YYYY-MM-DD.jsonld for that Sun..Sat range.
- Recurses through JSONLD_DIR so it works whether your JSON-LD is flat or
  organized into subfolders per hall/day.
- Loads JSONLD_DIR from .env (defaults to data/jsonld).
"""

from __future__ import annotations
import os
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

def sunday_of(d: date) -> date:
    # Sunday on or before d
    return d - timedelta(days=(d.weekday() + 1) % 7)

def main():
    load_dotenv()
    jsonld_dir = Path(os.getenv("JSONLD_DIR", "data/jsonld")).resolve()

    today = date.today()
    last_sunday = sunday_of(today) - timedelta(days=7)
    week = [last_sunday + timedelta(days=i) for i in range(7)]

    if not jsonld_dir.exists():
        print(f"JSON-LD dir not found: {jsonld_dir}")
        return

    print(f"Cleaning previous week JSON-LD in: {jsonld_dir}")
    print(f"Week to delete: {week[0]} .. {week[-1]}")

    deleted = 0
    for day in week:
        suffix = f"_{day.isoformat()}.jsonld"
        # walk all subfolders too
        for p in jsonld_dir.rglob(f"*{suffix}"):
            try:
                p.unlink()
                deleted += 1
                print(f"  ✂︎ {p}")
            except Exception as e:
                print(f"  ! Could not delete {p}: {e}")

    print(f"Done. Deleted {deleted} file(s).")

if __name__ == "__main__":
    main()