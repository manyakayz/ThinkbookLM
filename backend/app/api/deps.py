from __future__ import annotations
import hmac
from typing import Optional
from fastapi import Depends, HTTPException, Request, status

from app.config import get_settings
from app.models.user import User
from app.repositories import sessions as sessions_repo
from app.repositories import users as users_repo
from app.services import db


def _extract_token(request: Request) -> tuple[str | None, bool]:
    """Extract session token from cookie or Authorization header.
    
    Returns (token, is_cookie).
    """
    settings = get_settings()
    # 1. Primary: HttpOnly cookie
    cookie_token = request.cookies.get(settings.session_cookie_name)
    if cookie_token:
        return cookie_token, True

    # 2. Secondary: Bearer authorization header (useful for automated testing / CLI)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return token, False

    return None, False


def get_current_user(request: Request) -> User:
    """FastAPI dependency to enforce authentication and retrieve the current user."""
    token, is_cookie = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    pool = db.get_pool()
    with pool.connection() as conn:
        session = sessions_repo.get(conn, token)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = users_repo.get_by_id(conn, session.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Attach session metadata to request state
    request.state.session = session
    request.state.is_cookie_auth = is_cookie
    return user


def get_optional_current_user(request: Request) -> Optional[User]:
    """Dependency that returns User if authenticated, or None if unauthenticated."""
    try:
        return get_current_user(request)
    except HTTPException:
        return None


def verify_csrf(request: Request, current_user: User = Depends(get_current_user)) -> None:
    """CSRF protection dependency for state-changing requests.
    
    Only enforces CSRF when authentication is cookie-based. If Bearer token
    is used (e.g. API tests), CSRF header is not required.
    """
    is_cookie = getattr(request.state, "is_cookie_auth", False)
    if not is_cookie:
        return

    # Safe HTTP methods are exempt from CSRF
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    csrf_header = request.headers.get("X-CSRF-Token")
    session = getattr(request.state, "session", None)

    if not csrf_header or not session or not session.csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing.",
        )

    if not hmac.compare_digest(csrf_header.strip(), session.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token.",
        )
