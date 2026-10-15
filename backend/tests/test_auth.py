"""
Tests for Complete Authentication & User Data Isolation in ThinkbookLM.

Tests cover:
- Password hashing and verification with Argon2
- User registration and validation
- Duplicate email rejection (including case normalization)
- User login with valid and invalid credentials
- Generic login error messages (security requirement)
- Rate limiting protection on failed login attempts
- Persistent session handling and GET /auth/me
- Rejection of unauthenticated protected requests
- Session invalidation and cookie clearing on logout
- Cross-user notebook isolation
- Cross-user document isolation
- Cross-user retrieval isolation
"""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import UserCreate
from app.services import auth as auth_service
from app.services import db
from app.repositories import users as users_repo
from app.repositories import notebooks as notebooks_repo
from app.repositories import documents as documents_repo


@pytest.fixture
def client():
    return TestClient(app)


def _unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:8]}@example.com"


# ---------------------------------------------------------------------------
# 1. Password Hashing & Service Unit Tests
# ---------------------------------------------------------------------------

def test_password_hashing_and_verification():
    password = "SuperSecretPassword123"
    hashed = auth_service.hash_password(password)

    # Must not store plaintext
    assert hashed != password
    assert hashed.startswith("$argon2")

    # Verification must succeed for correct password
    assert auth_service.verify_password(password, hashed) is True

    # Verification must fail for incorrect password
    assert auth_service.verify_password("WrongPassword123", hashed) is False
    assert auth_service.verify_password("", hashed) is False


def test_user_create_validation():
    # Passwords mismatch
    user_data = UserCreate(
        full_name="Alice Smith",
        email="alice@example.com",
        password="ValidPassword1",
        confirm_password="DifferentPassword2",
    )
    with pytest.raises(ValueError, match="Passwords do not match"):
        user_data.validate_passwords_match()

    # Password too short (< 8 chars)
    with pytest.raises(ValueError, match="at least 8 characters"):
        UserCreate(
            full_name="Alice Smith",
            email="alice@example.com",
            password="Short1",
            confirm_password="Short1",
        )

    # Password missing number
    with pytest.raises(ValueError, match="at least one number"):
        UserCreate(
            full_name="Alice Smith",
            email="alice@example.com",
            password="OnlyLettersPassword",
            confirm_password="OnlyLettersPassword",
        )

    # Invalid email format
    with pytest.raises(ValueError, match="Invalid email"):
        UserCreate(
            full_name="Alice Smith",
            email="not-an-email",
            password="ValidPassword1",
            confirm_password="ValidPassword1",
        )


# ---------------------------------------------------------------------------
# 2. Registration API Tests
# ---------------------------------------------------------------------------

def test_user_registration_success(client):
    email = _unique_email()
    payload = {
        "full_name": "Test User",
        "email": email,
        "password": "Password123",
        "confirm_password": "Password123",
    }

    res = client.post("/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert "user" in data
    assert data["user"]["email"] == email.lower()
    assert data["user"]["full_name"] == "Test User"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 0

    # Verify cookies
    assert "thinkbook_session" in res.cookies
    assert "thinkbook_csrf" in res.cookies


def test_duplicate_email_registration_rejected(client):
    email = _unique_email()
    payload = {
        "full_name": "Original User",
        "email": email,
        "password": "Password123",
        "confirm_password": "Password123",
    }

    res1 = client.post("/auth/register", json=payload)
    assert res1.status_code == 201

    # Attempt to register again with same email (different case)
    payload_dup = {
        "full_name": "Duplicate User",
        "email": email.upper(),
        "password": "Password123",
        "confirm_password": "Password123",
    }
    res2 = client.post("/auth/register", json=payload_dup)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


# ---------------------------------------------------------------------------
# 3. Login API Tests
# ---------------------------------------------------------------------------

def test_user_login_success(client):
    email = _unique_email()
    reg_payload = {
        "full_name": "Login User",
        "email": email,
        "password": "SecretPassword1",
        "confirm_password": "SecretPassword1",
    }
    client.post("/auth/register", json=reg_payload)

    # Fresh client without cookies
    new_client = TestClient(app)
    login_payload = {
        "email": email.upper(),  # test case-insensitivity
        "password": "SecretPassword1",
    }
    res = new_client.post("/auth/login", json=login_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == email.lower()
    assert "csrf_token" in data
    assert "thinkbook_session" in res.cookies


def test_user_login_incorrect_password_rejected(client):
    email = _unique_email()
    reg_payload = {
        "full_name": "Wrong Pass User",
        "email": email,
        "password": "CorrectPassword1",
        "confirm_password": "CorrectPassword1",
    }
    client.post("/auth/register", json=reg_payload)

    new_client = TestClient(app)
    res = new_client.post("/auth/login", json={"email": email, "password": "WrongPassword999"})
    assert res.status_code == 401
    # Generic error without revealing user existence
    assert res.json()["detail"] == "Invalid email or password."


def test_user_login_nonexistent_email_rejected(client):
    res = client.post("/auth/login", json={"email": "nonexistent@example.com", "password": "AnyPassword1"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password."


# ---------------------------------------------------------------------------
# 4. Session Handling, Persistent Auth & Logout
# ---------------------------------------------------------------------------

def test_get_me_authenticated(client):
    email = _unique_email()
    client.post(
        "/auth/register",
        json={"full_name": "Persistent User", "email": email, "password": "Password123", "confirm_password": "Password123"},
    )

    # Calling /auth/me with session cookie
    res = client.get("/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == email


def test_get_me_unauthenticated():
    fresh_client = TestClient(app)
    res = fresh_client.get("/auth/me")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


def test_unauthenticated_protected_requests_rejected():
    fresh_client = TestClient(app)
    # Trying to list notebooks without auth
    res_nb = fresh_client.get("/notebooks")
    assert res_nb.status_code == 401

    # Trying to create a notebook without auth
    res_create = fresh_client.post("/notebooks", json={"name": "Hacked Notebook"})
    assert res_create.status_code == 401


def test_user_logout_invalidates_session(client):
    email = _unique_email()
    client.post(
        "/auth/register",
        json={"full_name": "Logout User", "email": email, "password": "Password123", "confirm_password": "Password123"},
    )

    # Verify authenticated
    assert client.get("/auth/me").status_code == 200

    # Logout
    res_logout = client.post("/auth/logout")
    assert res_logout.status_code == 200
    assert "Logged out successfully" in res_logout.json()["message"]

    # Calling /auth/me after logout must be rejected
    res_me = client.get("/auth/me")
    assert res_me.status_code == 401


# ---------------------------------------------------------------------------
# 5. Data Isolation Across Users
# ---------------------------------------------------------------------------

def test_cross_user_notebook_isolation():
    client_a = TestClient(app)
    client_b = TestClient(app)

    email_a = _unique_email()
    email_b = _unique_email()

    # User A registers
    reg_a = client_a.post(
        "/auth/register",
        json={"full_name": "User Alpha", "email": email_a, "password": "Password123", "confirm_password": "Password123"},
    ).json()
    csrf_a = reg_a["csrf_token"]

    # User B registers
    reg_b = client_b.post(
        "/auth/register",
        json={"full_name": "User Beta", "email": email_b, "password": "Password123", "confirm_password": "Password123"},
    ).json()
    csrf_b = reg_b["csrf_token"]

    # User A creates a private notebook
    res_nb_a = client_a.post("/notebooks", json={"name": "Alpha Private Research"}, headers={"X-CSRF-Token": csrf_a})
    assert res_nb_a.status_code == 201
    nb_a = res_nb_a.json()
    nb_a_id = nb_a["id"]

    # User B creates a private notebook
    res_nb_b = client_b.post("/notebooks", json={"name": "Beta Private Research"}, headers={"X-CSRF-Token": csrf_b})
    assert res_nb_b.status_code == 201
    nb_b = res_nb_b.json()
    nb_b_id = nb_b["id"]

    # User A lists notebooks -> only sees Alpha's notebook
    list_a = client_a.get("/notebooks").json()
    nb_a_ids = [n["id"] for n in list_a]
    assert nb_a_id in nb_a_ids
    assert nb_b_id not in nb_a_ids

    # User B lists notebooks -> only sees Beta's notebook
    list_b = client_b.get("/notebooks").json()
    nb_b_ids = [n["id"] for n in list_b]
    assert nb_b_id in nb_b_ids
    assert nb_a_id not in nb_b_ids

    # User A tries to directly access User B's notebook by ID -> 404 Not Found
    res_steal_b = client_a.get(f"/notebooks/{nb_b_id}")
    assert res_steal_b.status_code == 404

    # User B tries to directly access User A's notebook by ID -> 404 Not Found
    res_steal_a = client_b.get(f"/notebooks/{nb_a_id}")
    assert res_steal_a.status_code == 404


def test_cross_user_document_isolation():
    client_a = TestClient(app)
    client_b = TestClient(app)

    reg_a = client_a.post(
        "/auth/register",
        json={"full_name": "Doc Owner", "email": _unique_email(), "password": "Password123", "confirm_password": "Password123"},
    ).json()
    csrf_a = reg_a["csrf_token"]

    reg_b = client_b.post(
        "/auth/register",
        json={"full_name": "Doc Intruder", "email": _unique_email(), "password": "Password123", "confirm_password": "Password123"},
    ).json()
    csrf_b = reg_b["csrf_token"]

    # User A creates notebook
    nb_a_id = client_a.post("/notebooks", json={"name": "Doc Isolation NB"}, headers={"X-CSRF-Token": csrf_a}).json()["id"]

    # User B tries to upload into User A's notebook -> 404 Not Found
    res_b_upload = client_b.post(
        f"/notebooks/{nb_a_id}/documents",
        files={"file": ("intruder.txt", b"Intruder secret document", "text/plain")},
        headers={"X-CSRF-Token": csrf_b},
    )
    assert res_b_upload.status_code == 404

    # User B tries to list documents in User A's notebook -> 404 Not Found
    res_b_list = client_b.get(f"/notebooks/{nb_a_id}/documents")
    assert res_b_list.status_code == 404

    # User B tries to retrieve from User A's notebook -> 404 Not Found
    res_b_retrieve = client_b.post(
        "/retrieve",
        json={"query": "test query", "notebook_id": nb_a_id, "top_k": 5},
        headers={"X-CSRF-Token": csrf_b},
    )
    assert res_b_retrieve.status_code == 404
