"""
Minimal client for the Fellow Aiden cloud API.

Replaces the `fellow-aiden` package, which was dropped for three reasons:

  1. Stale. Last release 0.2.2 (March 2025), last commit July 2025, with an
     open "push a new version to pip" issue over a year old.
  2. Wrong against the current API. It reads brew profiles from a 'profiles'
     key inside the device payload. That key no longer exists, so the library
     raises KeyError on connect — which meant carrying two monkey-patches.
  3. GPL-3.0, while Coffee Dial is MIT.

Endpoints are the same ones the package used; this is a reimplementation of
the wire protocol, not of its code.

Two deliberate differences in behaviour:

  * Nothing here logs the auth response. The package logged it at DEBUG,
    putting the account's accessToken and long-lived refreshToken on stdout.
  * A missing or unexpected field raises. The package's fallback behaviour
    turned Fellow's schema change into a silent "0 profiles" on an account
    that had 22, which is the failure mode that hid the bug for months.

The session is per-instance. The package used a class-level requests.Session,
so every instance shared one set of auth headers.
"""

import requests

BASE_URL = "https://l8qtmnc692.execute-api.us-west-2.amazonaws.com/v1"

API_AUTH = "/auth/login"
API_DEVICES = "/devices"
API_PROFILES = "/devices/{id}/profiles"
API_PROFILE = "/devices/{id}/profiles/{pid}"

# Fellow's API rejects the stock python-requests agent.
USER_AGENT = "Fellow/5 CFNetwork/1568.300.101 Darwin/24.2.0"

TIMEOUT_S = 30

# Server-assigned fields that must not be sent back when creating a profile.
SERVER_SIDE_PROFILE_FIELDS = (
    "id", "createdAt", "updatedAt", "deletedAt", "deviceId", "lastUsedTime",
    "sharedFrom", "isDefaultProfile", "instantBrew", "folder", "duration",
    "lastGBQuantity", "synced",
)


class AidenError(Exception):
    """Any failure talking to the Aiden cloud API."""


class AidenAuthError(AidenError):
    """Login was rejected, or the session could not be renewed."""


class AidenClient:
    """Talks to one Fellow account's brewer.

    Credentials are held for the lifetime of the instance so an expired
    access token can be renewed transparently. They are never logged.
    """

    def __init__(self, email, password, base_url=BASE_URL, timeout=TIMEOUT_S):
        self._email = email
        self._password = password
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})

        self._device = None
        self.authenticate()

    # ─── Auth ────────────────────────────────────────────────────────────────

    def authenticate(self):
        """Exchange email and password for a bearer token.

        The response body is never logged or returned — it carries a
        long-lived refreshToken.
        """
        try:
            response = self._session.post(
                self._base_url + API_AUTH,
                json={"email": self._email, "password": self._password},
                timeout=self._timeout,
            )
        except requests.RequestException as e:
            raise AidenError("Could not reach Fellow's API: {}".format(e))

        try:
            parsed = response.json()
        except ValueError:
            raise AidenAuthError(
                "Login returned a non-JSON response (HTTP {}).".format(response.status_code)
            )

        token = parsed.get("accessToken")
        if not token:
            raise AidenAuthError("Email or password incorrect.")

        self._session.headers.update({"Authorization": "Bearer " + token})

    # ─── Request plumbing ────────────────────────────────────────────────────

    def _request(self, method, path, **kwargs):
        """Send a request, renewing the token once on a 401."""
        url = self._base_url + path
        kwargs.setdefault("timeout", self._timeout)

        try:
            response = self._session.request(method, url, **kwargs)
            if response.status_code == 401:
                self.authenticate()
                response = self._session.request(method, url, **kwargs)
        except requests.RequestException as e:
            raise AidenError("{} {} failed: {}".format(method, path, e))

        return response

    def _json(self, method, path, **kwargs):
        """Send a request and require a successful JSON body back."""
        response = self._request(method, path, **kwargs)

        if response.status_code >= 400:
            raise AidenError(
                "{} {} returned HTTP {}: {}".format(
                    method, path, response.status_code, response.text[:200]
                )
            )

        if not response.content:
            return None

        try:
            return response.json()
        except ValueError:
            raise AidenError(
                "{} {} returned a non-JSON body.".format(method, path)
            )

    # ─── Device ──────────────────────────────────────────────────────────────

    def device(self, refresh=False):
        """The brewer on this account. Assumes one, like the Fellow app does."""
        if self._device is not None and not refresh:
            return self._device

        devices = self._json("GET", API_DEVICES, params={"dataType": "real"})

        if not isinstance(devices, list) or not devices:
            raise AidenError("No brewer found on this Fellow account.")

        device = devices[0]
        if "id" not in device:
            raise AidenError(
                "Device payload has no 'id'. Fellow's API schema may have changed."
            )

        self._device = device
        return device

    @property
    def brewer_id(self):
        return self.device()["id"]

    @property
    def display_name(self):
        return self.device().get("displayName") or "Aiden"

    # ─── Profiles ────────────────────────────────────────────────────────────

    def get_profiles(self):
        """Every brew profile on the brewer.

        Profiles come from their own endpoint. They are NOT in the device
        payload, whatever the fellow-aiden package believed.
        """
        profiles = self._json("GET", API_PROFILES.format(id=self.brewer_id))

        if not isinstance(profiles, list):
            raise AidenError(
                "Profiles endpoint returned {} rather than a list. "
                "Fellow's API schema may have changed.".format(type(profiles).__name__)
            )

        return profiles

    def get_profile_by_id(self, pid):
        for profile in self.get_profiles():
            if profile.get("id") == pid:
                return profile
        return None

    def create_profile(self, data):
        """Create a profile. Server-assigned fields are stripped first."""
        payload = {k: v for k, v in data.items() if k not in SERVER_SIDE_PROFILE_FIELDS}

        if not payload.get("title"):
            raise AidenError("A profile needs a title.")

        created = self._json(
            "POST", API_PROFILES.format(id=self.brewer_id), json=payload
        )

        if not isinstance(created, dict) or "id" not in created:
            raise AidenError("Profile was not created: {}".format(created))

        return created

    def delete_profile(self, pid):
        """Delete one profile by id.

        Irreversible on the physical brewer. The caller is responsible for
        confirming intent; this checks only that the profile exists, so a
        typo'd id fails loudly instead of quietly doing nothing.
        """
        if self.get_profile_by_id(pid) is None:
            raise AidenError("No profile with id {!r} on this brewer.".format(pid))

        response = self._request("DELETE", API_PROFILE.format(id=self.brewer_id, pid=pid))

        if response.status_code >= 400:
            raise AidenError(
                "Delete failed with HTTP {}: {}".format(
                    response.status_code, response.text[:200]
                )
            )

        return True
