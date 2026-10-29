"""
FastAPI 应用主入口
- 生命周期管理：启动时初始化数据库、预置管理员、配置日志
- 中间件：CORS、限流（slowapi）
- 路由注册：认证、聊天、会话、知识库
- 生产模式：托管前端静态文件
"""
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import settings
from .database import init_db
from .auth import seed_admin
from .api import auth, chat, session, knowledge


# ==================== 日志系统（按天轮转） ====================

def setup_logging():
    log_dir = os.path.join(os.path.dirname(settings.upload_dir), "logs")
    os.makedirs(log_dir, exist_ok=True)

    handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO if not settings.debug else logging.DEBUG)

    # 减少第三方库日志噪音
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# ==================== 限流器 ====================

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


# ==================== 应用生命周期 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- 启动时 ----
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info(f"  {settings.app_name} 启动中...")
    logger.info("=" * 50)

    # 确保数据目录存在
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.chroma_path, exist_ok=True)

    # 初始化数据库表
    await init_db()
    logger.info("数据库表初始化完成")

    # 预置管理员账号
    await seed_admin()
    logger.info(f"管理员账号就绪: {settings.admin_username}")

    if settings.embedding_provider == "local_onnx" and settings.embedding_configured:
        import asyncio
        from .rag import get_embeddings
        await asyncio.to_thread(get_embeddings)
        logger.info("本地 BGE-M3 向量模型加载完成")

    logger.info("应用初始化完成；实际监听地址见 Uvicorn 启动日志")
    yield

    # ---- 关闭时 ----
    logger.info("应用关闭")


# ==================== 创建应用 ====================

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="基于 LangChain 的电商知识库问答演示项目",
    lifespan=lifespan,
)

# 注册限流器
app.state.limiter = limiter

# 限流超限处理器
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "请求过于频繁，请稍后再试"},
    )

# 安装限流中间件
app.add_middleware(SlowAPIMiddleware)

# CORS 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 注册路由 ====================

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(chat.router, prefix="/api/chat", tags=["聊天"])
app.include_router(session.router, prefix="/api/sessions", tags=["会话"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])


# ==================== 健康检查 ====================

@app.get("/api/health", summary="健康检查")
async def health_check():
    return {
        "status": "ok", "app": settings.app_name,
        "service": "ecommerce-rag-showcase",
        "llm_configured": settings.llm_configured,
        "embedding_configured": settings.embedding_configured,
        "llm_model": settings.llm_model,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
    }


# ==================== 生产模式：托管前端静态文件 ====================

FRONTEND_DIST = os.path.join(
    os.path.dirname(__file__), "..", "..", "frontend", "dist"
)

if os.path.exists(FRONTEND_DIST):
    from fastapi.staticfiles import StaticFiles

    @app.get("/")
    async def serve_frontend_index():
        from starlette.responses import FileResponse
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")),
        name="assets",
    )
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_frontend_route(path: str):
        # BrowserRouter 的页面刷新仍返回入口；未知 API 保留真实 404。
        from fastapi import HTTPException
        from starlette.responses import FileResponse
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
    logging.getLogger(__name__).info("生产模式：前端静态文件已挂载")
