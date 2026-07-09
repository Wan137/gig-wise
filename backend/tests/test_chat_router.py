"""Tests for chat session management and the SSE message endpoint.

Session CRUD and validation need no LLM and always run. The actual
send-a-message flow calls the real graph (no mocking) and is skipped without
a configured Groq key, matching the rest of the suite.
"""
from __future__ import annotations

import pytest

from app.config import get_settings

requires_groq = pytest.mark.skipif(
    not get_settings().groq_api_key, reason="GROQ_API_KEY not configured - skipping live LLM tests"
)


def test_create_and_list_sessions(client, auth_headers):
    create_resp = client.post("/chat/sessions", headers=auth_headers)
    assert create_resp.status_code == 201
    assert create_resp.json()["title"] == "New conversation"

    list_resp = client.get("/chat/sessions", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_sessions_require_authentication(client):
    response = client.get("/chat/sessions")
    assert response.status_code == 401


def test_messages_404_for_nonexistent_session(client, auth_headers):
    response = client.get("/chat/sessions/does-not-exist/messages", headers=auth_headers)
    assert response.status_code == 404


def test_messages_404_for_another_users_session(client, auth_headers):
    # Session belongs to fixture-user; a second, different user must not see it.
    session_id = client.post("/chat/sessions", headers=auth_headers).json()["id"]

    client.post("/auth/signup", json={"email": "other@example.com", "password": "roadwarrior123"})
    other_login = client.post("/auth/login", data={"username": "other@example.com", "password": "roadwarrior123"})
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    response = client.get(f"/chat/sessions/{session_id}/messages", headers=other_headers)
    assert response.status_code == 404


def test_empty_message_is_rejected(client, auth_headers):
    session_id = client.post("/chat/sessions", headers=auth_headers).json()["id"]
    response = client.post(
        f"/chat/sessions/{session_id}/messages", headers=auth_headers, json={"content": "   "}
    )
    assert response.status_code == 422


@requires_groq
def test_send_message_streams_trace_and_final_events(client, auth_headers):
    session_id = client.post("/chat/sessions", headers=auth_headers).json()["id"]

    response = client.post(
        f"/chat/sessions/{session_id}/messages",
        headers=auth_headers,
        json={"content": "Hi, what can you help me with?"},
    )

    assert response.status_code == 200
    assert "event: trace" in response.text
    assert "event: final" in response.text

    history = client.get(f"/chat/sessions/{session_id}/messages", headers=auth_headers).json()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"

    # First message should have set the session title.
    sessions = client.get("/chat/sessions", headers=auth_headers).json()
    assert sessions[0]["title"] == "Hi, what can you help me with?"
