"""
聊天 API：SSE 流式问答
性能优化：流式输出降低首字延迟 + 限流保护
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..schemas import ChatRequest
from ..models import User, ChatSession, ChatMessage
from ..database import get_db
from ..auth import get_current_user
from ..rag import retrieve_with_sources, stream_rag_response
from ..config import settings

router = APIRouter()


@router.post("/stream", summary="流式问答（SSE）")
async def chat_stream(
    req: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    SSE 流式问答接口：
    1. 保存用户消息
    2. 检索知识库
    3. 先发 sources 事件
    4. 流式发送 chunk 事件
    5. 最后发 done 事件
    """
    # ---- 限流检查（使用 slowapi app.state） ----
    limiter = request.app.state.limiter
    if limiter:
        # 手动检查限流
        pass  # slowapi 中间件会自动处理

    # ---- 校验会话归属 ----
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == req.session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )

    if not settings.llm_configured or not settings.embedding_configured:
        raise HTTPException(
            status_code=503,
            detail="模型接口尚未配置。请填写 backend/.env 的聊天与 Embedding 配置，然后重启服务。",
        )

    # 检索成功后再记录问题，接口配置错误不会产生无法回答的历史消息。
    try:
        context, sources = await retrieve_with_sources(req.question)
    except Exception:
        logging.getLogger(__name__).warning("知识库检索失败，请检查 Embedding 接口与模型配置")
        raise HTTPException(status_code=502, detail="知识库检索失败，请检查 Embedding 接口、模型和网络。")

    # ---- 保存用户消息 ----
    user_msg = ChatMessage(
        session_id=req.session_id,
        role="user",
        content=req.question,
    )
    db.add(user_msg)
    await db.commit()

    # ---- 更新会话时间 ----
    from datetime import datetime
    session.updated_at = datetime.utcnow()
    await db.commit()

    async def generate():
        # 1. 发送引用来源
        sources_data = json.dumps(
            {"type": "sources", "data": sources},
            ensure_ascii=False,
        )
        yield f"data: {sources_data}\n\n"

        # 2. 流式生成回答
        full_answer = ""
        try:
            async for chunk in stream_rag_response(req.question, context):
                full_answer += chunk
                chunk_data = json.dumps(
                    {"type": "chunk", "data": chunk},
                    ensure_ascii=False,
                )
                yield f"data: {chunk_data}\n\n"
        except Exception:
            logging.getLogger(__name__).warning("聊天模型生成失败，请检查接口、模型与网络")
            error_data = json.dumps({"type": "error", "data": "模型生成失败，请检查聊天接口、模型和网络后重试。"}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            return

        # 3. 保存 AI 消息到数据库（在流结束后）
        async with async_session_from_db() as write_db:
            ai_msg = ChatMessage(
                session_id=req.session_id,
                role="assistant",
                content=full_answer,
                sources=sources if sources else None,
            )
            write_db.add(ai_msg)
            await write_db.commit()
            msg_id = ai_msg.id

        # 4. 发送完成信号
        done_data = json.dumps(
            {"type": "done", "message_id": msg_id},
            ensure_ascii=False,
        )
        yield f"data: {done_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


# 用于在流式完成后独立写数据库的 session
from ..database import async_session as _async_session_factory

def async_session_from_db():
    """创建独立的数据库会话（用于流式完成后的写入）"""
    return _async_session_factory()
