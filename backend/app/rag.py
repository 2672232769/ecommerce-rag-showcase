"""
RAG 核心管道：文档加载、分割、向量化、检索、生成
性能优化：Embedding 缓存 + 检索 TTL 缓存 + 全局单例

注意：阿里百炼 OpenAI 兼容端点对 embedding input 格式与官方 OpenAI 有差异，
openai 2.x 库会预 tokenize 导致兼容失败，故使用自定义 Embeddings 类。
"""
from __future__ import annotations

import os
import asyncio
import httpx
from functools import lru_cache
from typing import Optional, Any, List
from cachetools import TTLCache
from langchain_core.embeddings import Embeddings
from langchain_community.document_loaders import TextLoader, PyPDFLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import chromadb
from chromadb.config import Settings as ChromaSettings
from .config import settings

# ==================== 自定义 Embedding 类（绕过 openai 库的 tokenize 行为） ====================

class AliyunEmbeddings(Embeddings):
    """阿里百炼 OpenAI 兼容 embedding 客户端
    直接用 httpx 发送原始字符串，避免 openai 库自动 tokenize 导致的兼容问题。
    """

    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 30.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """同步批量调用 embedding 接口"""
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": texts},
            )
            r.raise_for_status()
            data = r.json()
            # 按 index 排序，确保返回顺序与输入一致
            items = sorted(data["data"], key=lambda x: x.get("index", 0))
            return [item["embedding"] for item in items]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量向量化文档（langchain Embeddings 接口）"""
        # 阿里百炼单次请求最多 10 条文本，超出则分批
        batch_size = 10
        results: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            results.extend(self._embed(batch))
        return results

    def embed_query(self, text: str) -> List[float]:
        """单文本向量化（langchain Embeddings 接口）"""
        return self._embed([text])[0]


# ==================== 全局单例 ====================

_vectorstore: Optional[Any] = None
_embeddings: Optional[Embeddings] = None
_llm: Optional[ChatOpenAI] = None
_chroma_client: Optional[Any] = None

# ==================== 缓存 ====================

# Embedding 缓存：相同文本不重复调用 API
@lru_cache(maxsize=128)
def _embed_query_cached(text: str) -> list:
    """缓存的 embed_query 包装层"""
    return tuple(get_embeddings().embed_query(text))

# 检索结果 TTL 缓存：热点问题 10 分钟内直接返回
_retrieval_cache: TTLCache = TTLCache(maxsize=256, ttl=600)


# ==================== 获取器 ====================

def get_embeddings() -> Embeddings:
    global _embeddings
    if _embeddings is None:
        if settings.embedding_provider == "local_onnx":
            from .local_embeddings import LocalBgeM3Embeddings
            _embeddings = LocalBgeM3Embeddings(
                settings.embedding_local_path, settings.embedding_max_tokens, settings.embedding_threads,
            )
        else:
            _embeddings = AliyunEmbeddings(
                api_key=settings.embedding_api_key or settings.openai_api_key,
                base_url=settings.embedding_base_url or settings.openai_base_url,
                model=settings.embedding_model,
            )
    return _embeddings


def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        options = {}
        if settings.llm_thinking:
            options["extra_body"] = {"thinking": {"type": settings.llm_thinking}}
        _llm = ChatOpenAI(
            model=settings.llm_model,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_base_url,
            streaming=True,
            temperature=0.3,
            timeout=60,
            max_retries=1,
            max_tokens=settings.llm_max_tokens,
            **options,
        )
    return _llm


def get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(settings.chroma_path, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        os.makedirs(settings.chroma_path, exist_ok=True)
        embeddings = get_embeddings()
        _vectorstore = Chroma(
            client=get_chroma_client(),
            persist_directory=settings.chroma_path,
            embedding_function=embeddings,
            collection_name="langchain",
        )
    return _vectorstore


def reset_vectorstore():
    """重置向量库实例（知识库变更后调用）"""
    global _vectorstore
    _vectorstore = None


# ==================== 文件加载器工厂 ====================

def _get_loader(file_path: str, file_type: str):
    loaders = {
        ".txt": lambda: TextLoader(file_path, encoding="utf-8"),
        ".md": lambda: TextLoader(file_path, encoding="utf-8"),
        ".pdf": lambda: PyPDFLoader(file_path),
        ".csv": lambda: CSVLoader(file_path, encoding="utf-8"),
    }
    if file_type not in loaders:
        raise ValueError(f"不支持的文件类型: {file_type}，支持: {list(loaders.keys())}")
    return loaders[file_type]()


# ==================== 异步文档处理（性能优化：线程池） ====================

async def process_document(file_path: str, filename: str, doc_id: int) -> int:
    """异步处理文档：加载 → 分割 → 向量化 → 存入 ChromaDB"""
    ext = os.path.splitext(filename)[1].lower()
    loader = _get_loader(file_path, ext)

    # 在默认线程池中执行同步 I/O 操作
    raw_docs = await asyncio.to_thread(loader.load)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
    )
    chunks = await asyncio.to_thread(text_splitter.split_documents, raw_docs)

    # 为每个 chunk 添加元数据（用于后续删除溯源）
    for chunk in chunks:
        chunk.metadata["source"] = filename
        chunk.metadata["doc_id"] = str(doc_id)

    vectorstore = get_vectorstore()
    await asyncio.to_thread(vectorstore.add_documents, chunks)
    await asyncio.to_thread(vectorstore.persist)

    # 知识库变更 → 清空缓存
    clear_caches()
    reset_vectorstore()

    return len(chunks)


async def delete_document_chunks(doc_id: int):
    """从向量库中删除指定文档的所有向量块"""
    vectorstore = get_vectorstore()
    await asyncio.to_thread(vectorstore._collection.delete, where={"doc_id": str(doc_id)})
    clear_caches()
    reset_vectorstore()


# ==================== RAG 检索与生成 ====================

async def retrieve_with_sources(query: str, top_k: int = 4) -> tuple[str, list[dict]]:
    """检索知识库，返回 (打包上下文, 引用来源列表)"""
    cache_key = f"{query}:{top_k}"
    if cache_key in _retrieval_cache:
        return _retrieval_cache[cache_key]

    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
    docs = await asyncio.to_thread(retriever.invoke, query)

    if not docs:
        return "", []

    sources = [
        {
            "source": doc.metadata.get("source", "未知来源"),
            "content": doc.page_content.strip(),
        }
        for doc in docs
    ]
    context = "\n\n---\n\n".join(doc.page_content for doc in docs)

    _retrieval_cache[cache_key] = (context, sources)
    return context, sources


async def stream_rag_response(question: str, context: str):
    """流式生成 RAG 回答（异步生成器）"""
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个电商平台的专业客服助手。请根据以下知识库中的商品信息，准确、友好地回答用户的问题。

规则：
1. 只根据知识库中的信息回答，如果知识库中没有相关信息，请礼貌地告知用户，并建议联系人工客服。
2. 简洁直接回答用户所问的内容，不要补充用户未问的商品信息。每项商品事实都必须能在知识库中找到依据，不得用常识扩展商品特性或结论。
3. 如果用户的问题涉及多个商品的比较，请列出对比信息。
4. 回复中使用 Markdown 格式（加粗、列表、表格等），让内容更清晰易读。
5. 文档未提供某项信息，只能说明信息不足，不能据此推断商品不具备该特性、不安全或不适用于某类人群。

知识库内容：
{context}"""),
        ("human", "{question}"),
    ])

    chain = prompt | llm | StrOutputParser()

    async for chunk in chain.astream({"context": context, "question": question}):
        yield chunk


def clear_caches():
    """清空所有缓存（知识库变更时调用）"""
    _retrieval_cache.clear()
    _embed_query_cached.cache_clear()
