"""pytest 全局配置"""
import sys
import os
import tempfile
from pathlib import Path

# 将 backend 目录加入模块搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 在导入 app 前隔离数据和凭据；测试永远不读写学习用数据库或调用真实模型。
test_root = Path(__file__).resolve().parents[2] / ".cache" / "tests"
test_root.mkdir(parents=True, exist_ok=True)
test_data = Path(tempfile.mkdtemp(prefix="run-", dir=test_root))
os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///" + (test_data / "app.db").as_posix(),
    "CHROMA_PATH": str(test_data / "chroma"),
    "UPLOAD_DIR": str(test_data / "uploads"),
    "OPENAI_API_KEY": "", "EMBEDDING_API_KEY": "",
    "OPENAI_BASE_URL": "http://127.0.0.1:1/v1",
    "EMBEDDING_BASE_URL": "http://127.0.0.1:1/v1",
    "LLM_MODEL": "test-only", "EMBEDDING_MODEL": "test-only",
    "EMBEDDING_PROVIDER": "api", "LLM_THINKING": "",
    "JWT_SECRET": "isolated-test-secret-with-no-real-service-access",
    "ADMIN_USERNAME": "admin", "ADMIN_PASSWORD": "123456", "DEBUG": "false",
})
