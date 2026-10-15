from __future__ import annotations
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import _extract_token, get_current_user
from app.config import get_settings
from app.models.user import AuthResponse, User, UserCreate, UserLogin, UserResponse
from app.repositories import sessions as sessions_repo
from app.repositories import users as users_repo
from app.services import auth as auth_service
from app.services import db

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(
    response: Response,
    session_id: str,
    csrf_token: str,
) -> None:
    settings = get_settings()
    # 1. HttpOnly session cookie
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.session_max_age_seconds,
        path="/",
    )
    # 2. Readable CSRF cookie for client header injection
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.session_max_age_seconds,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    response.delete_cookie(key=settings.csrf_cookie_name, path="/")


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, response: Response):
    """Register a new user account with secure Argon2 hashing and established session."""
    try:
        data.validate_passwords_match()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    pool = db.get_pool()
    with pool.connection() as conn:
        if users_repo.exists_by_email(conn, data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists.",
            )

        password_hash = auth_service.hash_password(data.password)
        user = users_repo.create(
            conn,
            full_name=data.full_name,
            email=data.email,
            password_hash=password_hash,
        )

        # Establish session immediately upon registration
        settings = get_settings()
        session_id = auth_service.generate_session_token()
        csrf_token = auth_service.generate_csrf_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_max_age_days)

        sessions_repo.create(
            conn,
            session_id=session_id,
            user_id=user.id,
            csrf_token=csrf_token,
            expires_at=expires_at,
        )
        conn.commit()

    _set_auth_cookies(response, session_id, csrf_token)
    return AuthResponse(
        user=UserResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            created_at=user.created_at,
        ),
        csrf_token=csrf_token,
    )


@router.post("/login", response_model=AuthResponse)
def login(data: UserLogin, request: Request, response: Response):
    """Authenticate with email and password, establishing an HTTP-only session."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{data.email}:{client_ip}"

    if auth_service.is_rate_limited(rate_limit_key) or auth_service.is_rate_limited(data.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again in 5 minutes.",
        )

    pool = db.get_pool()
    with pool.connection() as conn:
        user = users_repo.get_by_email(conn, data.email)
        if not user or not auth_service.verify_password(data.password, user.password_hash):
            auth_service.record_failed_login(rate_limit_key)
            auth_service.record_failed_login(data.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        # Clear failed login record on successful authentication
        auth_service.clear_failed_logins(rate_limit_key)
        auth_service.clear_failed_logins(data.email)

        # Create session
        settings = get_settings()
        session_id = auth_service.generate_session_token()
        csrf_token = auth_service.generate_csrf_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_max_age_days)

        sessions_repo.create(
            conn,
            session_id=session_id,
            user_id=user.id,
            csrf_token=csrf_token,
            expires_at=expires_at,
        )
        conn.commit()

    _set_auth_cookies(response, session_id, csrf_token)
    return AuthResponse(
        user=UserResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            created_at=user.created_at,
        ),
        csrf_token=csrf_token,
    )


@router.post("/logout")
def logout(request: Request, response: Response):
    """Invalidate session in database and clear HTTP-only cookies."""
    token, _ = _extract_token(request)
    if token:
        pool = db.get_pool()
        with pool.connection() as conn:
            sessions_repo.delete(conn, token)
            conn.commit()

    _clear_auth_cookies(response)
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=AuthResponse)
def get_me(request: Request, current_user: User = Depends(get_current_user)):
    """Retrieve the currently authenticated user's profile and active CSRF token."""
    session = getattr(request.state, "session", None)
    csrf_token = session.csrf_token if session else ""
    return AuthResponse(
        user=UserResponse(
            id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email,
            created_at=current_user.created_at,
        ),
        csrf_token=csrf_token,
    )
