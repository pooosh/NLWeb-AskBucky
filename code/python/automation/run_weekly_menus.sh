#!/usr/bin/env bash
set -euo pipefail

# === Adjust these paths if your layout differs ===
PROJECT_ROOT="$HOME/AskBucky/NLWeb"
VENV_PATH="$PROJECT_ROOT/myenv"
LOG_DIR="$PROJECT_ROOT/logs"
RAW_DIR="${RAW_DIR:-$PROJECT_ROOT/raw_menus}"
JSONLD_DIR="${JSONLD_DIR:-$PROJECT_ROOT/data/jsonld}"

mkdir -p "$LOG_DIR"

# Activate venv + env vars
# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"
# Load .env so fetch/transform pick up config
set -a
[ -f "$PROJECT_ROOT/.env" ] && source "$PROJECT_ROOT/.env"
set +a

# Helpful for SSL on macOS cron (harmless elsewhere)
export SSL_CERT_FILE="$(python -c 'import certifi; print(certifi.where())' 2>/dev/null || echo "")"

# Compute Sundays
PYDATE='
from datetime import date, timedelta
today = date.today()
this_sunday = today - timedelta(days=(today.weekday()+1)%7)
prev_sunday = this_sunday - timedelta(days=7)
print(this_sunday.isoformat(), prev_sunday.isoformat())
'
read -r THIS_SUNDAY PREV_SUNDAY < <(python -c "$PYDATE")

echo "=== [$(date -Is)] Weekly menu job starting ==="
echo "This Sunday: $THIS_SUNDAY"
echo "Prev Sunday: $PREV_SUNDAY"

cd "$PROJECT_ROOT"

# 0) Clean previous week JSON-LD (Sun..Sat) **before** fetching/transforming
#    This removes any files ending with _YYYY-MM-DD.jsonld for last week's dates.
echo "--- Pruning last week's JSON-LD (Sun..Sat) ---"
if [[ -d "$JSONLD_DIR" ]]; then
  python - "$JSONLD_DIR" <<'PY'
from pathlib import Path
import sys
from datetime import date, timedelta

jsonld_dir = Path(sys.argv[1])

today = date.today()
this_sunday = today - timedelta(days=(today.weekday()+1)%7)
prev_sunday = this_sunday - timedelta(days=7)
week = [prev_sunday + timedelta(days=i) for i in range(7)]

print(f"Cleaning in: {jsonld_dir}")
print(f"Week to delete: {week[0]} .. {week[-1]}")

deleted = 0
for d in week:
    suffix = f"_{d.isoformat()}.jsonld"
    for p in jsonld_dir.rglob(f"*{suffix}"):
        try:
            p.unlink()
            print(f"  ✂︎ {p}")
            deleted += 1
        except Exception as e:
            print(f"  ! Could not delete {p}: {e}")

print(f"Deleted {deleted} file(s).")
PY
else
  echo "JSONLD_DIR not found: $JSONLD_DIR (skipping prune)"
fi

# 1) Fetch weekly raw JSON (for THIS_SUNDAY)
echo "--- Fetching raw Nutrislice menus ---"
python pyscripts/fetch_menu.py

# 2) Transform to JSON-LD (targets THIS_SUNDAY internally)
echo "--- Transforming raw -> JSON-LD ---"
python pyscripts/nutrislice_to_jsonld.py

# (Old step removed) We already pruned the whole previous week before generating.

echo "=== [$(date -Is)] Weekly menu job done ==="
