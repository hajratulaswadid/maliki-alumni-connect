import os
import shutil
import sys
import urllib.parse
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
    def _fix_path(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if "__route__" in qs:
            route = qs.pop("__route__")[0]
            new_query = urllib.parse.urlencode(qs, doseq=True)
            self.path = route + ("?" + new_query if new_query else "")
        elif self.path in ("/api/index.py", "/api/index", "/api", "/api/"):
            self.path = "/"

    def do_GET(self):
        self._fix_path()
        return super().do_GET()

    def do_POST(self):
        self._fix_path()
        return super().do_POST()

    def do_PUT(self):
        self._fix_path()
        return super().do_PUT()

    def do_DELETE(self):
        self._fix_path()
        return super().do_DELETE()

    def do_OPTIONS(self):
        self._fix_path()
        return super().do_OPTIONS()
