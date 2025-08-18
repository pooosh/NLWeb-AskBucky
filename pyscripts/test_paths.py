#!/usr/bin/env python3
from pathlib import Path

# Get the script's directory and resolve paths relative to NLWeb root
SCRIPT_DIR = Path(__file__).parent
NLWEB_ROOT = SCRIPT_DIR.parent
RAW_ROOT = NLWEB_ROOT / "raw_menus"
JSONLD_ROOT = NLWEB_ROOT / "data" / "jsonld"

print(f"Script dir: {SCRIPT_DIR}")
print(f"NLWeb root: {NLWEB_ROOT}")
print(f"Raw root: {RAW_ROOT}")
print(f"JSONLD root: {JSONLD_ROOT}")
print(f"Raw root exists: {RAW_ROOT.exists()}")
print(f"JSONLD root exists: {JSONLD_ROOT.exists()}")

# Test creating a file
test_file = RAW_ROOT / "test.txt"
test_file.write_text("test")
print(f"Created test file: {test_file}")
print(f"Test file exists: {test_file.exists()}") 