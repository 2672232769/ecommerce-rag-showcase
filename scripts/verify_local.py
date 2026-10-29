"""HTTP smoke check against the real local service; never calls an external model."""
import json
from pathlib import Path
import re
import sys

import httpx

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "docs" / "qa" / "runtime-state.json"
phase = sys.argv[1] if len(sys.argv) > 1 else "before"
with httpx.Client(base_url="http://127.0.0.1:8018", trust_env=False, timeout=10) as client:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["service"] == "ecommerce-rag-showcase"
    pages = {}
    for route in ("/", "/login", "/register", "/chat", "/profile", "/admin/knowledge"):
        response = client.get(route)
        assert response.status_code == 200 and '<div id="root">' in response.text
        pages[route] = response.status_code
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', client.get("/").text)
    assert len(assets) >= 2
    for asset in assets:
        assert client.get(asset).status_code == 200
    assert client.get("/api/unknown").status_code == 404
    response = client.post("/api/auth/login", json={"username": "admin", "password": "123456"})
    assert response.status_code == 200
    client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
    assert client.get("/api/knowledge/documents").status_code == 200
    if phase == "before":
        response = client.post("/api/sessions", json={"title": "学习记录：本地部署检查（待接模型）"})
        assert response.status_code == 200
        session = response.json()
        STATE.write_text(json.dumps({"session_id": session["id"], "title": session["title"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        session = json.loads(STATE.read_text(encoding="utf-8"))
        session["id"] = session["session_id"]
    detail = client.get(f"/api/sessions/{session['id']}")
    assert detail.status_code == 200 and detail.json()["title"] == session["title"]
    if not health.json()["llm_configured"]:
        response = client.post("/api/chat/stream", json={"session_id": session["id"], "question": "星河 K87 多少钱？"})
        assert response.status_code == 503
        assert "尚未配置" in response.json()["detail"]
        assert client.get(f"/api/sessions/{session['id']}").json()["messages"] == []
    report = {"phase": phase, "status": "passed", "health": health.json(), "page_http_status": pages, "assets_checked": assets, "session_persisted": session["id"], "browser_interaction": "not verified", "real_llm": "not verified"}
    (ROOT / "docs" / "qa" / f"runtime-{phase}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
