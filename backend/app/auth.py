"""
认证模块：密码哈希、JWT 令牌、用户鉴权依赖、管理员预置
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .config import settings
from .database import get_db, async_session
from .models import User

logger = logging.getLogger(__name__)

# ------ 密码哈希 ------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ------ JWT 令牌 ------
security_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=settings.jwt_expire_hours)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")


# ------ 依赖注入：获取当前用户 ------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 JWT 令牌解析当前登录用户"""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=["HS256"],
            options={"verify_exp": True},
        )
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            logger.warning("JWT 缺少 sub 字段")
            raise credentials_exception
        user_id = int(user_id_raw)
    except (JWTError, ValueError, TypeError) as e:
        logger.warning(f"JWT 解析失败: {e}")
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        logger.warning(f"JWT 用户不存在: user_id={user_id}")
        raise credentials_exception
    return user


# ------ 依赖注入：管理员权限校验 ------

async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """校验当前用户是否为管理员"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


# ------ 管理员账号预置 ------

async def seed_admin():
    """首次启动时自动创建管理员账号"""
    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.username == settings.admin_username)
        )
        admin = result.scalar_one_or_none()
        if admin is None:
            admin = User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                role="admin",
            )
            db.add(admin)
            await db.commit()
