"""Run after filling backend/.env. Calls one embedding and one short chat request."""
import asyncio
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT / "backend")
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings
from app.rag import get_embeddings, get_llm


async def main():
    if not settings.llm_configured or not settings.embedding_configured:
        print("NOT CONFIGURED: check chat settings and local embedding files / embedding API settings.")
        return 2
    try:
        vector = await asyncio.to_thread(get_embeddings().embed_query, "学习测试：键盘价格")
        print(f"Embedding OK: dimension={len(vector)}")
    except Exception as error:
        print(f"Embedding FAILED ({type(error).__name__}); check endpoint, key, model and network.")
        return 1
    try:
        result = await get_llm().ainvoke("请只回复：连接成功")
        print(f"Chat OK: returned {len(result.content)} characters.")
    except Exception as error:
        print(f"Chat FAILED ({type(error).__name__}); check endpoint, key, model and network.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
