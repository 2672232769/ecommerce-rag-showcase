"""
Pydantic 数据校验模型
定义所有 API 的请求体和响应体结构
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ==================== 用户相关 ====================

class UserRegister(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class UserLogin(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")


# ==================== 会话相关 ====================

class SessionCreate(BaseModel):
    title: Optional[str] = "新对话"


class SessionUpdate(BaseModel):
    title: str


class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    sources: Optional[List[Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SessionDetailResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse]

    class Config:
        from_attributes = True


# ==================== 聊天相关 ====================

class ChatRequest(BaseModel):
    session_id: int = Field(..., description="会话ID")
    question: str = Field(..., min_length=1, max_length=5000, description="用户问题")


# ==================== 知识库相关 ====================

class KnowledgeDocResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


class KnowledgeReprocessResponse(BaseModel):
    id: int
    filename: str
    message: str
