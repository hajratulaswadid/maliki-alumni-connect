import os
import shutil
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Ensure writable DB in /tmp for Vercel serverless environment
tmp_dir = Path("/tmp/maliki_data")
try:
    tmp_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

tmp_db = tmp_dir / "maliki.db"
src_db = ROOT_DIR / "data" / "maliki.db"

if not tmp_db.exists() and src_db.exists():
    try:
        shutil.copy2(src_db, tmp_db)
    except Exception as e:
        print(f"Error copying DB: {e}")

os.environ["MALIKI_DB_PATH"] = str(tmp_db)
os.environ["MALIKI_DEMO"] = "1"

import app

# Initialize DB
try:
    app.init_db()
    if not tmp_db.exists() or tmp_db.stat().st_size == 0:
        app.seed_demo_data()
except Exception as e:
    print(f"DB Init error: {e}")

class handler(app.MalikiRequestHandler):
    pass
