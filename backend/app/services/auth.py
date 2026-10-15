from __future__ import annotations
from datetime import datetime, timedelta
import secrets
import threading
import time
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

# Argon2id password hasher with secure, standard parameters
_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Securely hash a password using Argon2id."""
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against an Argon2id hash.
    
    Returns False on mismatch or corrupted hash without raising exceptions.
    """
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def generate_session_token() -> str:
    """Generate a high-entropy, cryptographically secure session token."""
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_hex(32)


# --- Basic Rate Limiter for Login Attempts ---
# Tracks failed attempts per identifier (email or IP) to defend against brute force.
_lock = threading.Lock()
_failed_attempts: dict[str, list[float]] = {}
MAX_FAILED_ATTEMPTS = 5
WINDOW_SECONDS = 300  # 5 minutes


def record_failed_login(identifier: str) -> None:
    now = time.monotonic()
    with _lock:
        timestamps = _failed_attempts.setdefault(identifier.lower(), [])
        # Prune old entries
        cutoff = now - WINDOW_SECONDS
        _failed_attempts[identifier.lower()] = [t for t in timestamps if t > cutoff] + [now]


def is_rate_limited(identifier: str) -> bool:
    now = time.monotonic()
    cutoff = now - WINDOW_SECONDS
    with _lock:
        timestamps = _failed_attempts.get(identifier.lower(), [])
        recent = [t for t in timestamps if t > cutoff]
        _failed_attempts[identifier.lower()] = recent
        return len(recent) >= MAX_FAILED_ATTEMPTS


def clear_failed_logins(identifier: str) -> None:
    with _lock:
        _failed_attempts.pop(identifier.lower(), None)
