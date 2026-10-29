"""Local entrypoint. Run with backend/.venv, always keep data in backend/data."""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT / "backend")
sys.path.insert(0, str(ROOT / "backend"))
runtime = ROOT / ".runtime"
runtime.mkdir(exist_ok=True)
(runtime / "service.json").write_text(json.dumps({
    "pid": os.getpid(), "started_at": time.time(),
    "entrypoint": str(Path(__file__).resolve()), "url": "http://127.0.0.1:8018",
}), encoding="utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8018, log_level="info")
