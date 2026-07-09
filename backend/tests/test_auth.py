"""End-to-end tests for signup/login/me against a real (temp-file) SQLite DB.

Uses FastAPI's TestClient rather than mocking the DB layer, because the thing
actually worth verifying here is the full request -> validation -> hashing ->
DB -> JWT -> dependency-injection chain working together, not each piece in
isolation.
"""
from __future__ import annotations


def test_signup_creates_user(client):
    response = client.post(
        "/auth/signup",
        json={"email": "driver@example.com", "password": "roadwarrior123", "full_name": "Ah Kow"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "driver@example.com"
    assert body["full_name"] == "Ah Kow"
    assert "hashed_password" not in body  # never leak the hash, even hashed


def test_signup_rejects_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "roadwarrior123"}
    first = client.post("/auth/signup", json=payload)
    assert first.status_code == 201

    second = client.post("/auth/signup", json=payload)
    assert second.status_code == 409


def test_signup_rejects_weak_password(client):
    response = client.post("/auth/signup", json={"email": "weak@example.com", "password": "short"})
    assert response.status_code == 422


def test_signup_rejects_invalid_email(client):
    response = client.post("/auth/signup", json={"email": "not-an-email", "password": "roadwarrior123"})
    assert response.status_code == 422


def test_login_succeeds_with_correct_credentials(client):
    client.post("/auth/signup", json={"email": "rider@example.com", "password": "deliverypro123"})
    response = client.post(
        "/auth/login", data={"username": "rider@example.com", "password": "deliverypro123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_fails_with_wrong_password(client):
    client.post("/auth/signup", json={"email": "rider2@example.com", "password": "deliverypro123"})
    response = client.post(
        "/auth/login", data={"username": "rider2@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_login_fails_for_nonexistent_user(client):
    response = client.post(
        "/auth/login", data={"username": "ghost@example.com", "password": "whatever123"}
    )
    assert response.status_code == 401


def test_me_returns_current_user_with_valid_token(client):
    client.post("/auth/signup", json={"email": "me@example.com", "password": "roadwarrior123", "full_name": "Kartik"})
    login = client.post("/auth/login", data={"username": "me@example.com", "password": "roadwarrior123"})
    token = login.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_me_rejects_missing_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_rejects_tampered_token(client):
    client.post("/auth/signup", json={"email": "tamper@example.com", "password": "roadwarrior123"})
    login = client.post("/auth/login", data={"username": "tamper@example.com", "password": "roadwarrior123"})
    token = login.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}tampered"})
    assert response.status_code == 401
