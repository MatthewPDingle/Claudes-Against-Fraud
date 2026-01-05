"""
Rate limiting middleware
"""
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from config import settings
import redis

# Redis connection for rate limiting
redis_client = redis.from_url(settings.RATE_LIMIT_STORAGE_URL)

# Create limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.RATE_LIMIT_STORAGE_URL,
    enabled=settings.RATE_LIMIT_ENABLED
)


def get_rate_limit_for_user(trust_level: str) -> str:
    """
    Get rate limit string for user trust level

    Returns string like "100/minute"
    """
    limits = {
        "NEWCOMER": settings.RATE_LIMIT_NEWCOMER,
        "CONTRIBUTOR": settings.RATE_LIMIT_CONTRIBUTOR,
        "TRUSTED": settings.RATE_LIMIT_TRUSTED,
        "EXPERT": settings.RATE_LIMIT_EXPERT,
    }

    limit = limits.get(trust_level, settings.RATE_LIMIT_NEWCOMER)
    return f"{limit}/minute"


def check_rate_limit(user_id: str, trust_level: str, endpoint: str) -> tuple[bool, dict]:
    """
    Check if user has exceeded rate limit

    Returns:
        (is_allowed, limit_info)
    """
    limit = get_rate_limit_for_user(trust_level)
    limit_value = int(limit.split('/')[0])

    # Redis key for this user+endpoint
    key = f"rate_limit:{user_id}:{endpoint}"

    # Get current count
    current = redis_client.get(key)

    if current is None:
        # First request in this window
        redis_client.setex(key, 60, 1)  # Expire in 60 seconds
        return True, {
            "limit": limit_value,
            "remaining": limit_value - 1,
            "reset": 60
        }

    current = int(current)

    if current >= limit_value:
        # Rate limit exceeded
        ttl = redis_client.ttl(key)
        return False, {
            "limit": limit_value,
            "remaining": 0,
            "reset": ttl
        }

    # Increment counter
    redis_client.incr(key)

    return True, {
        "limit": limit_value,
        "remaining": limit_value - current - 1,
        "reset": redis_client.ttl(key)
    }


async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware to enforce rate limits
    """
    # Skip rate limiting for health checks and static files
    if request.url.path in ["/health", "/metrics"]:
        response = await call_next(request)
        return response

    # Get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)

    if user and settings.RATE_LIMIT_ENABLED:
        # Check rate limit
        is_allowed, limit_info = check_rate_limit(
            str(user.user_id),
            user.trust_level,
            request.url.path
        )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(limit_info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(limit_info["reset"]),
                    "Retry-After": str(limit_info["reset"])
                }
            )

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(limit_info["reset"])
        return response

    response = await call_next(request)
    return response
