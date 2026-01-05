"""
Authentication and authorization
"""
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime
import secrets
import hashlib

from database import get_db
from models import User, APIKey, Agent
from config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new API key"""
    return f"caf_sk_{secrets.token_urlsafe(settings.API_KEY_LENGTH)}"


def verify_api_key(db: Session, api_key: str) -> tuple[User, APIKey]:
    """
    Verify an API key and return the associated user and key

    Raises HTTPException if key is invalid
    """
    key_hash = hash_api_key(api_key)

    # Find API key
    db_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.revoked == False
    ).first()

    if not db_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key"
        )

    # Check expiration
    if db_key.expires_at and db_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired"
        )

    # Get user
    user = db.query(User).filter(User.user_id == db_key.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Check user status
    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is {user.status.lower()}"
        )

    # Update last used
    db_key.last_used = datetime.utcnow()
    db.commit()

    return user, db_key


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user

    Usage:
        @app.get("/protected")
        def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    api_key = credentials.credentials
    user, _ = verify_api_key(db, api_key)
    return user


async def get_current_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> APIKey:
    """
    Dependency to get current API key
    """
    api_key = credentials.credentials
    _, db_key = verify_api_key(db, api_key)
    return db_key


def check_scope(required_scope: str):
    """
    Decorator to check if API key has required scope

    Usage:
        @app.post("/findings")
        def create_finding(
            user: User = Depends(get_current_user),
            api_key: APIKey = Depends(get_current_api_key)
        ):
            check_scope("write:findings")(lambda: None, api_key)
            # Proceed with creation
    """
    def scope_checker(api_key: APIKey = Depends(get_current_api_key)):
        if required_scope not in api_key.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}"
            )
        return api_key
    return scope_checker


def get_agent_by_id(agent_id: str, db: Session, user: User) -> Agent:
    """
    Get agent by ID and verify ownership
    """
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Verify ownership
    if agent.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this agent"
        )

    return agent


def require_trust_level(min_level: str):
    """
    Decorator to require minimum trust level

    Trust levels (in order): NEWCOMER, CONTRIBUTOR, TRUSTED, EXPERT
    """
    trust_levels = {
        "NEWCOMER": 0,
        "CONTRIBUTOR": 1,
        "TRUSTED": 2,
        "EXPERT": 3
    }

    def level_checker(user: User = Depends(get_current_user)):
        user_level = trust_levels.get(user.trust_level, 0)
        required_level = trust_levels.get(min_level, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires trust level: {min_level}"
            )
        return user

    return level_checker
