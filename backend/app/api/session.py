"""
会话管理 API：创建、查看、删除会话，查看消息历史
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..schemas import (
    SessionCreate, SessionUpdate,
    SessionResponse, SessionDetailResponse, MessageResponse,
)
from ..models import User, ChatSession, ChatMessage
from ..database import get_db
from ..auth import get_current_user

router = APIRouter()


@router.post("", response_model=SessionResponse, summary="创建会话")
async def create_session(
    req: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建一个新的聊天会话"""
    session = ChatSession(
        user_id=current_user.id,
        title=req.title or "新对话",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionResponse.model_validate(session)


@router.get("", response_model=list[SessionResponse], summary="获取会话列表")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的所有会话（按更新时间倒序）"""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = result.scalars().all()
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionDetailResponse, summary="获取会话详情")
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取会话详情（含消息列表）"""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[MessageResponse.model_validate(m) for m in session.messages],
    )


@router.patch("/{session_id}", response_model=SessionResponse, summary="更新会话标题")
async def update_session(
    session_id: int,
    req: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改会话标题"""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    session.title = req.title
    session.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session)
    return SessionResponse.model_validate(session)


@router.delete("/{session_id}", summary="删除会话")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除会话及其所有消息"""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    await db.delete(session)
    await db.commit()
    return {"message": "会话已删除"}
