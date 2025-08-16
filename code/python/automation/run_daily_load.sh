#!/usr/bin/env bash
set -euo pipefail

# Robust daily loader: deletes yesterday's site, loads today's JSON-LD files
# Works even if .env sets JSONLD_DIR to a relative path.

# --- Resolve project locations ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
VENV_PATH="${VENV_PATH:-$PROJECT_ROOT/myenv}"

# Activate venv + env vars
cd "$PROJECT_ROOT/code/python"
# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"
set -a
[ -f "$PROJECT_ROOT/.env" ] && source "$PROJECT_ROOT/.env"
set +a

# Make local packages importable
export PYTHONPATH="$PROJECT_ROOT/code/python${PYTHONPATH:+:$PYTHONPATH}"

# Normalize JSONLD_DIR to an absolute path (handles relative in .env)
DEFAULT_JSONLD="$PROJECT_ROOT/data/jsonld"
JSONLD_DIR="${JSONLD_DIR:-$DEFAULT_JSONLD}"
if [[ "$JSONLD_DIR" != /* ]]; then
  JSONLD_DIR="$PROJECT_ROOT/${JSONLD_DIR#./}"
fi
# Collapse to canonical absolute path if it exists
if [[ -d "$JSONLD_DIR" ]]; then
  JSONLD_DIR="$(cd "$JSONLD_DIR" && pwd)"
fi

# Helpful for SSL on macOS cron (harmless elsewhere)
export SSL_CERT_FILE="$(python - <<'PY'
try:
    import certifi; print(certifi.where())
except Exception:
    print("")
PY
)"

# Compute TODAY and YESTERDAY (allow override via env TODAY=YYYY-MM-DD)
TODAY_ISO="${TODAY:-$(python - <<'PY'
from datetime import date
print(date.today().isoformat())
PY
)}"

YDAY_ISO="$(TODAY="$TODAY_ISO" python - <<'PY'
import os
from datetime import date, timedelta
iso = os.environ.get("TODAY")
base = date.fromisoformat(iso) if iso else date.today()
print((base - timedelta(days=1)).isoformat())
PY
)"

SITE_TODAY="menus_${TODAY_ISO}"
SITE_YDAY="menus_${YDAY_ISO}"

echo "=== Daily vector load ==="
echo "PROJECT_ROOT=$PROJECT_ROOT"
echo "PWD=$(pwd)"
echo "JSONLD_DIR=$JSONLD_DIR"
echo "Today:     $TODAY_ISO  (site: $SITE_TODAY)"
echo "Yesterday: $YDAY_ISO   (site: $SITE_YDAY)"
echo

# 1) Delete yesterday's site (ignore failure if empty/nonexistent)
echo "--- Deleting yesterday's site: $SITE_YDAY"
python -m data_loading.db_load --only-delete "$SITE_YDAY" || true
echo

# 2) Load today's files (any file ending with _YYYY-MM-DD.jsonld)
echo "--- Loading today's JSON-LD (*.jsonld ending with _${TODAY_ISO}.jsonld) from $JSONLD_DIR"
found=0
loaded=0

# Use find -print0 to be safe with spaces/apostrophes in filenames
while IFS= read -r -d '' file; do
  found=1
  echo "• $file"
  if python -m data_loading.db_load --force-recompute --batch-size 64 --database qdrant_local "$file" "$SITE_TODAY"; then
    loaded=$((loaded+1))
  else
    echo "  ! failed to load: $file"
  fi
done < <(find "$JSONLD_DIR" -type f -name "*_${TODAY_ISO}.jsonld" -print0)

if [[ $found -eq 0 ]]; then
  echo "No files matched *_${TODAY_ISO}.jsonld in $JSONLD_DIR"
  echo "Sample listing of JSON-LD dir (top 10):"
  ls -1 "$JSONLD_DIR" 2>/dev/null | head -10 || true
  exit 1
fi

echo
echo "Loaded $loaded file(s) for site $SITE_TODAY."
echo "=== Done ==="
