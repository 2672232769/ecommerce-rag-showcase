"""真实 HTTP/SQLite/Chroma 流程；测试替身仅用于外部模型，不能证明模型回答质量。"""
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings

from app.main import app
from app.config import settings
from app import rag
from app.api import chat


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as instance:
        yield instance


def auth(client, username="admin", password="123456"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def register(client):
    username = "qa_" + uuid4().hex[:12]
    response = client.post("/api/auth/register", json={"username": username, "password": "qa-pass-123"})
    assert response.status_code == 200, response.text
    return username, {"Authorization": "Bearer " + response.json()["access_token"]}


def test_health_and_spa_refresh(client):
    assert client.get("/api/health").json()["llm_configured"] is False
    for route in ("/", "/login", "/chat", "/profile", "/admin/knowledge"):
        response = client.get(route)
        assert response.status_code == 200
        assert '<div id="root">' in response.text
    assert client.get("/api/nonexistent").status_code == 404


def test_auth_and_password_change(client):
    username, headers = register(client)
    assert client.get("/api/auth/me", headers=headers).json()["role"] == "user"
    assert client.post("/api/auth/register", json={"username": username, "password": "qa-pass-123"}).status_code == 409
    assert client.post("/api/auth/change-password", headers=headers, json={"old_password": "wrong", "new_password": "changed-123"}).status_code == 400
    assert client.post("/api/auth/change-password", headers=headers, json={"old_password": "qa-pass-123", "new_password": "changed-123"}).status_code == 200
    assert client.post("/api/auth/login", json={"username": username, "password": "qa-pass-123"}).status_code == 401
    assert auth(client, username, "changed-123")


def test_user_and_session_isolation(client):
    _, first = register(client)
    _, second = register(client)
    created = client.post("/api/sessions", headers=first, json={"title": "独立会话"}).json()
    sid = created["id"]
    assert client.get(f"/api/sessions/{sid}", headers=second).status_code == 404
    assert client.patch(f"/api/sessions/{sid}", headers=second, json={"title": "other"}).status_code == 404
    assert client.delete(f"/api/sessions/{sid}", headers=second).status_code == 404
    assert client.post("/api/chat/stream", headers=second, json={"session_id": sid, "question": "test"}).status_code == 404
    assert client.get("/api/sessions", headers=second).json() == []
    assert client.get("/api/knowledge/documents", headers=second).status_code == 403
    assert client.post("/api/knowledge/upload", headers=second, files={"file": ("demo.txt", b"demo")}).status_code == 403
    assert client.patch(f"/api/sessions/{sid}", headers=first, json={"title": "重命名"}).status_code == 200
    assert client.delete(f"/api/sessions/{sid}", headers=first).status_code == 200
    assert client.get(f"/api/sessions/{sid}", headers=first).status_code == 404


def test_missing_credentials_are_explicit_and_no_message_saved(client):
    headers = auth(client)
    sid = client.post("/api/sessions", headers=headers, json={}).json()["id"]
    response = client.post("/api/chat/stream", headers=headers, json={"session_id": sid, "question": "测试"})
    assert response.status_code == 503
    assert "尚未配置" in response.json()["detail"]
    assert client.get(f"/api/sessions/{sid}", headers=headers).json()["messages"] == []
    assert client.post("/api/knowledge/upload", headers=headers, files={"file": ("demo.txt", b"demo")}).status_code == 503


class TestOnlyEmbeddings(Embeddings):
    """确定性非语义测试向量，绝不作为运行模式使用。"""
    __test__ = False

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        return [value / 255.0 for value in hashlib.sha256(text.encode()).digest()[:16]]


@pytest.fixture
def model_stubs(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-only-not-a-real-key")
    monkeypatch.setattr(rag, "_embeddings", TestOnlyEmbeddings())
    rag.reset_vectorstore()
    rag.clear_caches()

    async def fake_stream(question, context):
        assert "299" in context
        yield "【自动测试模型替身】"
        yield "键盘售价为299元。"

    monkeypatch.setattr(chat, "stream_rag_response", fake_stream)
    yield
    rag.reset_vectorstore()
    rag.clear_caches()


def test_upload_retrieve_stream_history_and_delete(client, model_stubs):
    headers = auth(client)
    response = client.post("/api/knowledge/upload", headers=headers, files={"file": ("qa-product.md", "键盘售价299元。支持蓝牙。".encode("utf-8"))})
    assert response.status_code == 200, response.text
    doc = response.json()
    assert doc["chunk_count"] == 1
    sid = client.post("/api/sessions", headers=headers, json={"title": "测试问答"}).json()["id"]
    response = client.post("/api/chat/stream", headers=headers, json={"session_id": sid, "question": "键盘多少钱"})
    assert response.status_code == 200, response.text
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert events[0]["type"] == "sources"
    assert events[0]["data"][0]["source"] == "qa-product.md"
    assert events[-1]["type"] == "done"
    # 使用新登录令牌重新读取 SQLite 中的历史，而非前端内存状态。
    detail = client.get(f"/api/sessions/{sid}", headers=auth(client)).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert "299" in detail["messages"][1]["content"]
    assert detail["messages"][1]["sources"][0]["source"] == "qa-product.md"
    assert client.delete(f"/api/knowledge/documents/{doc['id']}", headers=headers).status_code == 200
    assert rag.get_vectorstore()._collection.get(where={"doc_id": str(doc["id"])})["ids"] == []
    assert not (Path(settings.upload_dir) / str(doc["id"]) / doc["filename"]).exists()
    assert len(rag._retrieval_cache) == 0


def test_same_filename_keeps_independent_content(client, model_stubs):
    headers = auth(client)
    ids = []
    for content in (b"first 299", b"second 399"):
        response = client.post("/api/knowledge/upload", headers=headers, files={"file": ("same.txt", content)})
        assert response.status_code == 200, response.text
        ids.append(response.json()["id"])
    assert ids[0] != ids[1]
    assert (Path(settings.upload_dir) / str(ids[0]) / "same.txt").read_bytes() == b"first 299"
    assert client.delete(f"/api/knowledge/documents/{ids[0]}", headers=headers).status_code == 200
    assert (Path(settings.upload_dir) / str(ids[1]) / "same.txt").read_bytes() == b"second 399"
    assert client.delete(f"/api/knowledge/documents/{ids[1]}", headers=headers).status_code == 200


def test_invalid_uploads(client):
    headers = auth(client)
    for filename in ("../outside.txt", "C:outside.txt", "unsafe.exe"):
        assert client.post("/api/knowledge/upload", headers=headers, files={"file": (filename, b"test")}).status_code == 400


def test_stream_failure_has_error_event_and_no_fake_saved_answer(client, model_stubs, monkeypatch):
    async def fake_retrieve(question):
        return "context", []
    async def broken_stream(question, context):
        yield "partial"
        raise RuntimeError("test failure")
    monkeypatch.setattr(chat, "retrieve_with_sources", fake_retrieve)
    monkeypatch.setattr(chat, "stream_rag_response", broken_stream)
    headers = auth(client)
    sid = client.post("/api/sessions", headers=headers, json={}).json()["id"]
    response = client.post("/api/chat/stream", headers=headers, json={"session_id": sid, "question": "test failure"})
    assert '"type": "error"' in response.text
    assert '"type": "done"' not in response.text
    assert [m["role"] for m in client.get(f"/api/sessions/{sid}", headers=headers).json()["messages"]] == ["user"]
