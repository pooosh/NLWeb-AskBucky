# NLWeb/code/python/tasks.py
import os, sys, subprocess, datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # py3.8 fallback if needed

ROOT = os.path.dirname(__file__)
PYSCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "pyscripts")

def run(cmd: list[str], cwd: str = None) -> None:
    print(f"→ running: {' '.join(cmd)}", flush=True)
    working_dir = cwd if cwd else ROOT
    subprocess.run(cmd, check=True, cwd=working_dir, env=os.environ.copy())

def weekly():
    # Run scripts from pyscripts directory
    run(["python", "fetch_menu.py"], cwd=PYSCRIPTS_DIR)
    run(["python", "nutrislice_to_jsonld.py"], cwd=PYSCRIPTS_DIR)
    # Run cleanup script from current directory
    run(["python", "cleanup_jsonld_week.py"])

def daily():
    tz = os.getenv("LOCAL_TZ", "America/Chicago")
    today = datetime.datetime.now(ZoneInfo(tz)).date()
    yesterday = today - datetime.timedelta(days=1)
    print(f"📅 Today: {today}", flush=True)
    print(f"📅 Yesterday: {yesterday}", flush=True)

    # Check required environment variables for fetch_menu.py
    required_vars = ["NUTRISLICE_API_URL", "DINING_HALL_SLUGS", "MEAL_TYPES", "RAW_DIR"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}", flush=True)
        print("Available environment variables:", flush=True)
        for key, value in os.environ.items():
            if any(prefix in key for prefix in ["NUTRISLICE", "DINING", "MEAL", "RAW", "JSONLD"]):
                print(f"  {key}: {value}", flush=True)
        raise SystemExit(1)

    print("✅ All required environment variables are set", flush=True)

    # 1) Make sure JSON-LD for today exists in this container
    run(["python", "fetch_menu.py"], cwd=PYSCRIPTS_DIR)
    run(["python", "nutrislice_to_jsonld.py"], cwd=PYSCRIPTS_DIR)

    # 2) Load to Qdrant (and delete yesterday)
    os.environ["SITETAG_TODAY"] = f"menus_{today.isoformat()}"
    os.environ["SITETAG_YESTERDAY"] = f"menus_{yesterday.isoformat()}"
    run(["python", "load_today_to_qdrant.py", "--today", today.isoformat(), "--yesterday", yesterday.isoformat()])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python tasks.py [weekly|daily]", file=sys.stderr)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "weekly": weekly()
    elif cmd == "daily": daily()
    else:
        print(f"unknown command: {cmd}", file=sys.stderr); sys.exit(2)
