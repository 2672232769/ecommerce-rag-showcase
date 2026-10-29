"""
应用配置管理
所有配置项通过 .env 文件或环境变量设置
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Literal


class Settings(BaseSettings):
    # ========== LLM 配置 ==========
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-3.5-turbo"
    llm_max_tokens: int = 768
    llm_thinking: Literal["", "enabled", "disabled"] = ""

    # ========== Embedding 配置 ==========
    embedding_model: str = "text-embedding-3-small"
    # 留空时复用聊天接口，允许聊天与向量模型来自不同服务商。
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_provider: Literal["api", "local_onnx"] = "api"
    embedding_local_path: str = "../models/bge-m3-onnx-int8"
    embedding_max_tokens: int = 1024
    embedding_threads: int = 4

    # ========== JWT 安全配置 ==========
    jwt_secret: str = "change-me-in-production"
    jwt_expire_hours: int = 24

    # ========== 管理员账号 ==========
    admin_username: str = "admin"
    admin_password: str = "123456"

    # ========== 数据库路径 ==========
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    chroma_path: str = "./data/chroma"
    upload_dir: str = "./data/uploads"

    # ========== 应用配置 ==========
    app_name: str = "电商智能问答系统"
    debug: bool = True

    @property
    def llm_configured(self) -> bool:
        return bool(self.openai_api_key.strip() and self.llm_model.strip()) and not self.openai_api_key.startswith("sk-your-")

    @property
    def embedding_configured(self) -> bool:
        if self.embedding_provider == "local_onnx":
            directory = Path(self.embedding_local_path)
            return all((directory / name).is_file() for name in ("tokenizer.json", "onnx/model_int8.onnx"))
        key = self.embedding_api_key or self.openai_api_key
        return bool(key.strip() and self.embedding_model.strip()) and not key.startswith("sk-your-")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
