"""Check two real answers after restricting the prompt to requested facts."""
import json
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
report = []
with httpx.Client(base_url="http://127.0.0.1:8018", timeout=90, trust_env=False) as client:
    login = client.post("/api/auth/login", json={"username": "admin", "password": "123456"})
    login.raise_for_status()
    client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
    session = client.post("/api/sessions", json={"title": "DeepSeek 实测：简洁回答检查"})
    session.raise_for_status()
    sid = session.json()["id"]
    for question, required, excluded in [
        ("海风 T500 保温杯能放进微波炉吗？", "微波炉", "婴幼儿"),
        ("星河 K87 有几个颜色？", "颜色", "有三种颜色"),
    ]:
        response = client.post("/api/chat/stream", json={"session_id": sid, "question": question})
        response.raise_for_status()
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        answer = "".join(event["data"] for event in events if event["type"] == "chunk")
        passed = events[-1]["type"] == "done" and required in answer and excluded not in answer
        report.append({"session_id": sid, "question": question, "answer": answer, "passed": passed, "uses_test_doubles": False})
        print(json.dumps(report[-1], ensure_ascii=False), flush=True)
        assert passed
    (ROOT / "docs" / "qa" / "deepseek-answer-scope.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
