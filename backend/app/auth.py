#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI管理系统 - JWT认证系统
实现基于JWT Token的用户认证和会话管理
"""

from datetime import datetime, timedelta
from typing import Optional, Union
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, get_async_db
from app.models import User
from app.schemas import UserResponse, TokenResponse
from app import RoleEnum

settings = get_settings()

# 🔐 密码加密配置
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 🔑 JWT Token配置
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# 🛡️ HTTP Bearer认证
security = HTTPBearer(auto_error=False)

class AuthenticationError(Exception):
    """认证异常"""
    pass

class AuthorizationError(Exception):
    """授权异常"""
    pass

# 🔒 密码处理函数
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

def validate_password_strength(password: str) -> bool:
    """验证密码强度"""
    if len(password) < 6:
        return False
    
    # 可以添加更复杂的密码强度验证
    # has_upper = any(c.isupper() for c in password)
    # has_lower = any(c.islower() for c in password)
    # has_digit = any(c.isdigit() for c in password)
    
    return True

# 🎫 JWT Token处理函数
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """创建JWT刷新令牌"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # 刷新令牌7天有效
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 检查令牌类型
        token_type = payload.get("type")
        if token_type != "access":
            raise AuthenticationError("Invalid token type")
        
        # 检查过期时间
        exp = payload.get("exp")
        if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
            raise AuthenticationError("Token expired")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired")
    except jwt.JWTError:
        raise AuthenticationError("Invalid token")

def verify_refresh_token(token: str) -> dict:
    """验证刷新令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid refresh token")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Refresh token expired")
    except jwt.JWTError:
        raise AuthenticationError("Invalid refresh token")

# 👤 用户认证函数
def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """验证用户凭证"""
    try:
        # 支持用户名或邮箱登录
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            raise AuthenticationError("User account is disabled")
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
        
    except Exception as e:
        db.rollback()
        if isinstance(e, AuthenticationError):
            raise
        raise AuthenticationError(f"Authentication failed: {str(e)}")

async def authenticate_user_async(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """异步验证用户凭证"""
    from sqlalchemy import select
    
    try:
        # 支持用户名或邮箱登录
        result = await db.execute(
            select(User).where(
                (User.username == username) | (User.email == username)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            raise AuthenticationError("User account is disabled")
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        await db.commit()
        
        return user
        
    except Exception as e:
        await db.rollback()
        if isinstance(e, AuthenticationError):
            raise
        raise AuthenticationError(f"Authentication failed: {str(e)}")

def get_user_by_token(db: Session, token: str) -> Optional[User]:
    """通过Token获取用户信息"""
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            return None
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            return None
        
        return user
        
    except (AuthenticationError, ValueError):
        return None

async def get_user_by_token_async(db: AsyncSession, token: str) -> Optional[User]:
    """异步通过Token获取用户信息"""
    from sqlalchemy import select
    
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            return None
        
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            return None
        
        return user
        
    except (AuthenticationError, ValueError):
        return None

# 🔐 FastAPI依赖注入
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户 (同步版本)"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token = credentials.credentials
    user = get_user_by_token(db, token)
    
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_user_async(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """获取当前用户 (异步版本)"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token = credentials.credentials
    user = await get_user_by_token_async(db, token)
    
    if user is None:
        raise credentials_exception
    
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

async def get_current_active_user_async(
    current_user: User = Depends(get_current_user_async)
) -> User:
    """获取当前活跃用户 (异步版本)"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """获取当前管理员用户"""
    if not current_user.is_admin and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_admin_user_async(
    current_user: User = Depends(get_current_active_user_async)
) -> User:
    """获取当前管理员用户 (异步版本)"""
    if not current_user.is_admin and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

# 🎯 便捷认证函数
def login_user(db: Session, username: str, password: str) -> TokenResponse:
    """用户登录"""
    user = authenticate_user(db, username, password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    # 创建刷新令牌
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "username": user.username}
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )

async def login_user_async(db: AsyncSession, username: str, password: str) -> TokenResponse:
    """用户登录 (异步版本)"""
    user = await authenticate_user_async(db, username, password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    # 创建刷新令牌
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "username": user.username}
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )

def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
    """刷新访问令牌"""
    try:
        payload = verify_refresh_token(refresh_token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # 创建新的访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username, "role": user.role},
            expires_delta=access_token_expires
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,  # 刷新令牌保持不变
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user)
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

# 🔍 企业微信用户认证
def authenticate_wechat_user(db: Session, wechat_userid: str) -> Optional[User]:
    """通过企业微信用户ID认证"""
    try:
        user = db.query(User).filter(User.wechat_userid == wechat_userid).first()
        
        if not user or not user.is_active:
            return None
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
        
    except Exception:
        db.rollback()
        return None

def create_wechat_token(user: User) -> str:
    """为企业微信用户创建Token"""
    access_token_expires = timedelta(hours=24)  # 企业微信Token有效期更长
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "wechat": True
        },
        expires_delta=access_token_expires
    )
    return access_token

# 🛡️ 安全工具函数
def check_password_policy(password: str) -> tuple[bool, str]:
    """检查密码策略"""
    if len(password) < 6:
        return False, "密码长度不能少于6位"
    
    if len(password) > 50:
        return False, "密码长度不能超过50位"
    
    # 可以添加更多密码策略
    # if not any(c.isupper() for c in password):
    #     return False, "密码必须包含大写字母"
    
    return True, "密码符合要求"

def generate_password_reset_token(user_id: int) -> str:
    """生成密码重置令牌"""
    expire = datetime.utcnow() + timedelta(hours=1)  # 1小时有效
    data = {
        "sub": str(user_id),
        "type": "password_reset",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verify_password_reset_token(token: str) -> Optional[int]:
    """验证密码重置令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("type") != "password_reset":
            return None
        
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
        
    except (jwt.ExpiredSignatureError, jwt.JWTError, ValueError):
        return None

# 📊 认证统计
class AuthStats:
    """认证统计类"""
    
    @staticmethod
    def get_login_stats(db: Session, days: int = 30) -> dict:
        """获取登录统计"""
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 总登录次数 (通过最后登录时间估算)
        active_users = db.query(User).filter(
            User.last_login >= start_date,
            User.is_active == True
        ).count()
        
        # 按角色统计
        role_stats = db.query(
            User.role,
            func.count(User.id).label('count')
        ).filter(
            User.last_login >= start_date,
            User.is_active == True
        ).group_by(User.role).all()
        
        return {
            "active_users": active_users,
            "period_days": days,
            "role_distribution": dict(role_stats),
            "total_users": db.query(User).filter(User.is_active == True).count()
        }

if __name__ == "__main__":
    """认证模块测试"""
    print("🔐 AI管理系统认证模块测试")
    print("=" * 50)
    
    # 测试密码加密
    test_password = "test123456"
    hashed = get_password_hash(test_password)
    verified = verify_password(test_password, hashed)
    print(f"密码加密测试: {'✅' if verified else '❌'}")
    
    # 测试JWT Token
    test_data = {"sub": "1", "username": "test", "role": "admin"}
    token = create_access_token(test_data)
    payload = verify_token(token)
    print(f"JWT Token测试: {'✅' if payload.get('sub') == '1' else '❌'}")
    
    # 测试密码策略
    valid, msg = check_password_policy(test_password)
    print(f"密码策略测试: {'✅' if valid else '❌'} - {msg}")
    
    print("=" * 50)