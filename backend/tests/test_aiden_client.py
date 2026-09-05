"""Aiden client tests.

These pin the behaviours that the fellow-aiden package got wrong: reading
profiles from the wrong place, and turning a schema change into a silent
empty list. No network — every response is a stub.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiden import client as aiden_client  # noqa: E402
from aiden import AidenClient, AidenError, AidenAuthError  # noqa: E402


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text
        self.content = b"x" if body is not None else b""

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class FakeSession:
    """Stands in for requests.Session. Records calls, replays queued responses."""

    def __init__(self, routes):
        self.headers = {}
        self.routes = routes
        self.calls = []

    def _resolve(self, method, url):
        self.calls.append((method, url))
        # Longest fragment first: "/devices" is a substring of
        # "/devices/{id}/profiles", so the more specific route must win.
        ordered = sorted(self.routes.items(), key=lambda kv: -len(kv[0][1]))
        for (m, fragment), response in ordered:
            if m == method and fragment in url:
                if isinstance(response, list):
                    return response.pop(0) if len(response) > 1 else response[0]
                return response
        raise AssertionError("unexpected {} {}".format(method, url))

    def post(self, url, **kw):
        return self._resolve("POST", url)

    def request(self, method, url, **kw):
        return self._resolve(method, url)


AUTH_OK = FakeResponse(200, {"accessToken": "tok", "refreshToken": "refresh"})

# A device payload shaped like Fellow's real one: note there is no 'profiles'
# key. This is exactly what broke the fellow-aiden package.
DEVICE_OK = FakeResponse(200, [{"id": "FB_123", "displayName": "Aiden"}])


def build(routes, monkeypatch):
    session = FakeSession(routes)
    monkeypatch.setattr(aiden_client.requests, "Session", lambda: session)
    return session


# ─── Auth ─────────────────────────────────────────────────────────────────────

def test_bad_credentials_raise_auth_error(monkeypatch):
    build({("POST", "/auth/login"): FakeResponse(401, {"message": "nope"})}, monkeypatch)
    with pytest.raises(AidenAuthError):
        AidenClient("a@b.c", "wrong")


def test_successful_auth_sets_bearer_header(monkeypatch):
    session = build({
        ("POST", "/auth/login"): AUTH_OK,
        ("GET", "/devices"): DEVICE_OK,
    }, monkeypatch)
    AidenClient("a@b.c", "pw")
    assert session.headers["Authorization"] == "Bearer tok"


def test_non_json_login_raises(monkeypatch):
    build({("POST", "/auth/login"): FakeResponse(500)}, monkeypatch)
    with pytest.raises(AidenAuthError):
        AidenClient("a@b.c", "pw")


# ─── Device ───────────────────────────────────────────────────────────────────

def test_no_brewer_on_account_raises(monkeypatch):
    build({
        ("POST", "/auth/login"): AUTH_OK,
        ("GET", "/devices"): FakeResponse(200, []),
    }, monkeypatch)
    c = AidenClient("a@b.c", "pw")
    with pytest.raises(AidenError, match="No brewer"):
        c.device()


def test_device_without_id_raises_rather_than_guessing(monkeypatch):
    build({
        ("POST", "/auth/login"): AUTH_OK,
        ("GET", "/devices"): FakeResponse(200, [{"displayName": "Aiden"}]),
    }, monkeypatch)
    c = AidenClient("a@b.c", "pw")
    with pytest.raises(AidenError, match="schema may have changed"):
        c.device()


# ─── Profiles: the bug this client exists to fix ──────────────────────────────

def test_profiles_come_from_their_own_endpoint_not_the_device(monkeypatch):
    """The device payload has no 'profiles' key; the client must not care."""
    session = build({
        ("POST", "/auth/login"): AUTH_OK,
        ("GET", "/devices"): DEVICE_OK,
        ("GET", "/profiles"): FakeResponse(200, [{"id": "p0", "title": "One"},
                                                 {"id": "p1", "title": "Two"}]),
    }, monkeypatch)
    c = AidenClient("a@b.c", "pw")
    profiles = c.get_profiles()

    assert len(profiles) == 2
    assert any("/devices/FB_123/profiles" in url for _, url in session.calls)


def test_unexpected_profiles_shape_raises_instead_of_returning_empty(monkeypatch):
    """The failure that hid the bug: a schema change must be loud, not [] ."""
    build({
        ("POST", "/auth/login"): AUTH_OK,
        ("GET", "/devices"): DEVICE_OK,
        ("GET", "/profiles"): FakeResponse(200, {"message": "moved"}),
    }, monkeypatch)
    c = AidenClient("a@b.c", "pw")
    with pytest.raises(AidenError, match="schema may have changed"):
        c.get_profiles()


def test_profiles_http_error_raises(monkeypatch):
    build({
        ("POST", "/auth/login"): AUTH_OK,
        ("GET", "/devices"): DEVICE_OK,
        ("GET", "/profiles"): FakeResponse(404, {"message": "gone"}, text="gone"),
    }, monkeypatch)
    c = AidenClient("a@b.c", "pw")
    with pytest.raises(AidenError, match="HTTP 404"):
        c.get_profiles()


# ─── Token renewal ────────────────────────────────────────────────────────────

def test_401_triggers_one_reauth_and_retry(monkeypatch):
    session = build({
        ("POST", "/auth/login"): AUTH_OK,
        ("GET", "/devices"): [FakeResponse(401), DEVICE_OK],
    }, monkeypatch)
    c = AidenClient("a@b.c", "pw")
    assert c.brewer_id == "FB_123"
    # Two logins: the initial one, then the renewal after the 401.
    assert sum(1 for m, u in session.calls if "/auth/login" in u) == 2


# ─── Create and delete ────────────────────────────────────────────────────────

def test_create_strips_server_assigned_fields(monkeypatch):
    captured = {}

    class CapturingSession(FakeSession):
        def request(self, method, url, **kw):
            if method == "POST" and "/profiles" in url:
                captured.update(kw.get("json") or {})
            return self._resolve(method, url)

    session = CapturingSession({
        ("POST", "/auth/login"): AUTH_OK,
        ("GET", "/devices"): DEVICE_OK,
        ("POST", "/profiles"): FakeResponse(200, {"id": "p9", "title": "New"}),
    })
    monkeypatch.setattr(aiden_client.requests, "Session", lambda: session)

    c = AidenClient("a@b.c", "pw")
    c.create_profile({"title": "New", "ratio": 16, "id": "should-be-dropped",
                      "deviceId": "also-dropped", "lastUsedTime": 123})

    assert captured["title"] == "New"
    assert "id" not in captured
    assert "deviceId" not in captured
    assert "lastUsedTime" not in captured


def test_create_without_title_raises(monkeypatch):
    build({
        ("POST", "/auth/login"): AUTH_OK,
        ("GET", "/devices"): DEVICE_OK,
    }, monkeypatch)
    c = AidenClient("a@b.c", "pw")
    with pytest.raises(AidenError, match="needs a title"):
        c.create_profile({"ratio": 16})


def test_delete_unknown_id_raises_and_sends_no_delete(monkeypatch):
    session = build({
        ("POST", "/auth/login"): AUTH_OK,
        ("GET", "/devices"): DEVICE_OK,
        ("GET", "/profiles"): FakeResponse(200, [{"id": "p0", "title": "One"}]),
    }, monkeypatch)
    c = AidenClient("a@b.c", "pw")

    with pytest.raises(AidenError, match="No profile with id"):
        c.delete_profile("p99")

    assert not any(m == "DELETE" for m, _ in session.calls)


def test_delete_existing_profile_issues_delete(monkeypatch):
    session = build({
        ("POST", "/auth/login"): AUTH_OK,
        ("GET", "/devices"): DEVICE_OK,
        ("GET", "/profiles"): FakeResponse(200, [{"id": "p0", "title": "One"}]),
        ("DELETE", "/profiles/p0"): FakeResponse(200),
    }, monkeypatch)
    c = AidenClient("a@b.c", "pw")

    assert c.delete_profile("p0") is True
    assert any(m == "DELETE" and "/profiles/p0" in u for m, u in session.calls)


# ─── No credential logging ────────────────────────────────────────────────────

def test_auth_response_is_never_returned_or_stored(monkeypatch):
    build({
        ("POST", "/auth/login"): AUTH_OK,
        ("GET", "/devices"): DEVICE_OK,
    }, monkeypatch)
    c = AidenClient("a@b.c", "pw")

    # The refresh token must not be retained anywhere on the instance.
    blob = repr(vars(c))
    assert "refresh" not in blob
