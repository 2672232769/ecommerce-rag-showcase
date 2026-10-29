"""
认证 API：注册、登录、修改密码、获取当前用户
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..schemas import (
    UserRegister, UserLogin, UserResponse, TokenResponse, ChangePasswordRequest,
)
from ..models import User
from ..database import get_db
from ..auth import (
    hash_password, verify_password, create_access_token,
    get_current_user,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, summary="用户注册")
async def register(req: UserRegister, db: AsyncSession = Depends(get_db)):
    """注册新用户，注册成功直接返回 token"""
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        )

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(req: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户名密码登录，返回 JWT 令牌"""
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_current_user)):
    """通过 JWT 令牌获取当前登录用户信息"""
    return UserResponse.model_validate(current_user)


@router.post("/change-password", summary="修改密码")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户的登录密码"""
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误",
        )

    current_user.password_hash = hash_password(req.new_password)
    await db.commit()
    return {"message": "密码修改成功"}
