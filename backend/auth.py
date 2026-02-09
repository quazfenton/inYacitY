"""
Authentication utilities for Nocturne Event Platform
Provides JWT-based authentication and authorization functions
"""

from datetime import datetime, timedelta
from typing import Optional
import jwt
import os
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.users import UserAccount, UserStore, UserRole
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Initialize user store
user_store = UserStore()

# Get secret key from environment or use default (should be changed in production)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserAccount:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In a real implementation, you would fetch the user from the database
    # For now, we'll simulate by creating a mock user based on the payload
    # But since we don't have a real database User model, we'll return the payload info
    
    # For this implementation, we'll return the payload which contains user info
    return payload


async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserAccount:
    """Get current authenticated admin user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    
    # Check if user has admin role
    user_role = payload.get("role", "user")
    
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admin privileges required"
        )
    
    return payload


def require_api_key(api_key_header: str = Depends(lambda: os.getenv("ADMIN_API_KEY"))):
    """Dependency to require API key for admin endpoints"""
    def api_key_dependency(x_api_key: str = Depends(lambda x: x.headers.get("X-API-Key") if hasattr(x, 'headers') else None)):
        if not api_key_header:
            # If no API key is configured, skip validation (development mode)
            return True
        
        if not x_api_key or x_api_key != api_key_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key"
            )
        
        return True
    
    return api_key_dependency


# For backward compatibility, also provide a function that can be used directly as a dependency
async def require_admin_api_key(x_api_key: str = Depends(lambda: (lambda x: x.headers.get("X-API-Key"))(getattr(x, 'request', {}) if hasattr(x, 'request') else {}))):
    """Require API key for admin endpoints - simplified version"""
    admin_api_key = os.getenv("ADMIN_API_KEY")
    
    if not admin_api_key:
        # If no API key is configured, skip validation (development mode)
        return True
    
    if not x_api_key or x_api_key != admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    
    return True