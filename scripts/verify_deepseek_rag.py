"""Real local upload -> BGE-M3 -> Chroma -> DeepSeek SSE -> SQLite validation.

Uses only the project's synthetic demo products. Saves responses, never keys/tokens.
The --persisted mode only reads previously generated history after a restart.
"""
import json
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone
import httpx

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "qa" / "deepseek-live.json"


def login(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "123456"})
    response.raise_for_status()
    client.headers["Authorization"] = "Bearer " + response.json()["access_token"]


def main():
    with httpx.Client(base_url="http://127.0.0.1:8018", timeout=180, trust_env=False) as client:
        login(client)
        if "--persisted" in sys.argv:
            report = json.loads(REPORT.read_text(encoding="utf-8"))
            response = client.get(f"/api/sessions/{report['session_id']}")
            response.raise_for_status()
            messages = response.json()["messages"]
            assistants = [message for message in messages if message["role"] == "assistant"]
            assert [message["content"] for message in assistants] == [entry["answer"] for entry in report["questions"]]
            assert all(message["sources"] for message in assistants)
            report["history_after_restart"] = {"passed": True, "message_count": len(messages), "checked_at": datetime.now(timezone.utc).isoformat()}
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print("Persisted real answers and citations verified after restart.", flush=True)
            return

        health = client.get("/api/health").json()
        assert health["llm_configured"] and health["embedding_configured"]
        assert health["embedding_provider"] == "local_onnx"
        docs = client.get("/api/knowledge/documents").json()
        document = next((item for item in docs if item["filename"] == "demo_products.md"), None)
        if document is None:
            with (ROOT / "sample_data" / "demo_products.md").open("rb") as handle:
                response = client.post("/api/knowledge/upload", files={"file": ("demo_products.md", handle, "text/markdown")})
            response.raise_for_status()
            document = response.json()
        assert document["chunk_count"] > 0
        print(f"Real document indexed: {document['chunk_count']} chunks", flush=True)
        response = client.post("/api/sessions", json={"title": "DeepSeek 实测：商品问答与引用"})
        response.raise_for_status()
        session_id = response.json()["id"]
        report = {"checked_at": datetime.now(timezone.utc).isoformat(), "model": health["llm_model"], "embedding": health["embedding_model"], "document": document, "session_id": session_id, "uses_test_doubles": False, "questions": []}
        cases = [
            ("星河 K87 多少钱？支持哪些连接方式？", ["299", "蓝牙", "2.4"]),
            ("K87 键盘可以直接水洗吗？", ["断电"]),
            ("云杉 M2 鼠标的重量和电池容量是多少？", ["68", "500"]),
            ("非质量问题退货，谁承担运费？", ["买家"]),
            ("海风 T500 保温杯能放进微波炉吗？", ["微波炉"]),
            ("星河 K87 有几个颜色？请依据知识库回答。", []),
        ]
        try:
            for question, expected in cases:
                begin = time.perf_counter()
                first_chunk = None
                events = []
                with client.stream("POST", "/api/chat/stream", json={"session_id": session_id, "question": question}) as stream:
                    if stream.status_code != 200:
                        stream.read()
                        raise RuntimeError(f"Chat HTTP {stream.status_code}: {stream.text}")
                    for line in stream.iter_lines():
                        if line.startswith("data: "):
                            event = json.loads(line[6:])
                            events.append(event)
                            if event["type"] == "chunk" and event.get("data") and first_chunk is None:
                                first_chunk = time.perf_counter() - begin
                answer = "".join(event["data"] for event in events if event["type"] == "chunk")
                sources = next((event["data"] for event in events if event["type"] == "sources"), [])
                done = bool(events and events[-1]["type"] == "done")
                checked = all(term in answer for term in expected)
                if "水洗" in question:
                    checked = checked and bool(re.search("不[能支持可建议]*.*水洗|不能|不支持|不可以", answer))
                if "微波炉" in question:
                    checked = checked and bool(re.search("禁止|不能|不可以|不可", answer))
                if "颜色" in question:
                    checked = bool(re.search("没有.*颜色|未.*颜色|无法.*确定|没有提供|未提供|没有相关", answer))
                citation_ok = bool(sources) and all(source["source"] == "demo_products.md" for source in sources)
                passed = done and checked and citation_ok
                report["questions"].append({"question": question, "answer": answer, "sources": sources, "done": done, "passed": passed, "first_text_seconds": round(first_chunk, 3) if first_chunk is not None else None, "total_seconds": round(time.perf_counter() - begin, 3)})
                print(json.dumps({"question": question, "passed": passed, "answer": answer}, ensure_ascii=False), flush=True)
                assert passed, "Inspect saved answer/citation output; this is not an accuracy benchmark."
            login(client)
            detail = client.get(f"/api/sessions/{session_id}").json()
            assert len(detail["messages"]) == 2 * len(cases)
            report["history_after_login"] = True
            report["status"] = "passed"
        finally:
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
