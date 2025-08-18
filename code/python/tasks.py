# NLWeb/code/python/tasks.py
import os, sys, subprocess, datetime

def check_dependencies():
    """Check if required Python packages are available"""
    required_packages = ["openai", "qdrant_client"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required Python packages: {missing_packages}", flush=True)
        print("Please install: pip install " + " ".join(missing_packages), flush=True)
        return False
    
    print("✅ All required Python packages are available", flush=True)
    return True

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # py3.8 fallback if needed

ROOT = os.path.dirname(__file__)
PYSCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "pyscripts")

def run(cmd: list[str], cwd: str = None) -> None:
    print(f"→ running: {' '.join(cmd)}", flush=True)
    working_dir = cwd if cwd else ROOT
    print(f"→ working directory: {working_dir}", flush=True)
    try:
        subprocess.run(cmd, check=True, cwd=working_dir, env=os.environ.copy())
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}", flush=True)
        print(f"❌ Command: {' '.join(cmd)}", flush=True)
        print(f"❌ Working directory: {working_dir}", flush=True)
        raise

def weekly():
    # Run scripts from pyscripts directory
    run(["python", "fetch_menu.py"], cwd=PYSCRIPTS_DIR)
    run(["python", "nutrislice_to_jsonld.py"], cwd=PYSCRIPTS_DIR)
    # Run cleanup script from current directory
    run(["python", "cleanup_jsonld_week.py"])

def daily():
    print("🔄 Starting daily task...", flush=True)
    
    # Check environment variables
    required_env_vars = ["QDRANT_URL", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}", flush=True)
        raise SystemExit(1)
    
    tz = os.getenv("LOCAL_TZ", "America/Chicago")
    today = datetime.datetime.now(ZoneInfo(tz)).date()
    yesterday = today - datetime.timedelta(days=1)
    
    print(f"📅 Today: {today.isoformat()}", flush=True)
    print(f"📅 Yesterday: {yesterday.isoformat()}", flush=True)
    
    os.environ["SITETAG_TODAY"] = f"menus_{today.isoformat()}"
    os.environ["SITETAG_YESTERDAY"] = f"menus_{yesterday.isoformat()}"
    
    # Check if the script exists
    script_path = os.path.join(ROOT, "load_today_to_qdrant.py")
    if not os.path.exists(script_path):
        print(f"❌ Script not found: {script_path}", flush=True)
        raise SystemExit(1)
    
    print(f"✅ Script found: {script_path}", flush=True)
    
    run(["python", "load_today_to_qdrant.py", "--today", today.isoformat(), "--yesterday", yesterday.isoformat()])
    
    print("✅ Daily task completed successfully", flush=True)

if __name__ == "__main__":
    print(f"🚀 tasks.py started with args: {sys.argv}", flush=True)
    print(f"📁 Current working directory: {os.getcwd()}", flush=True)
    print(f"📁 Script directory: {ROOT}", flush=True)
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("usage: python tasks.py [weekly|daily]", file=sys.stderr)
        sys.exit(2)
    
    cmd = sys.argv[1]
    print(f"🎯 Executing command: {cmd}", flush=True)
    
    try:
        if cmd == "weekly": 
            weekly()
        elif cmd == "daily": 
            daily()
        else:
            print(f"unknown command: {cmd}", file=sys.stderr)
            sys.exit(2)
    except Exception as e:
        print(f"❌ Error executing {cmd}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
