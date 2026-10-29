"""
Client for Pyur Compal CH8978E cable modem.

DISCLAIMER: This library is vibe-coded and was developed through AI-assisted
exploration of an undocumented modem web interface without access to any official
API or manufacturer documentation. It may break without warning on firmware updates.
No liability is accepted for any damages, data loss, or security issues arising
from the use of this code. Use at your own risk.

Protocol notes (reverse-engineered from the web UI):
- Login: POST /actionHandler/check.php  →  {"status": "success", "AccessLevel": 1}
- Data:  GET  /internet_page/RgWanStatus.php  →  HTML with JSON embedded in JS var initP
- The CSRF_Token cookie is required and is set by the initial GET /
- Session token is stored in the sessionToken cookie
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_LOGGER = logging.getLogger(__name__)

# All paths are relative to the modem base URL
_PATH_ROOT = "/"
_PATH_LOGIN = "/actionHandler/check.php"
_PATH_WAN_STATUS = "/internet_page/RgWanStatus.php"

# Regex to extract the initP JS variable content from the page
_INIT_P_RE = re.compile(
    r"var\s+initP\s*=\s*\{(.*?)\}\s*\n\s*\$\s*\(function",
    re.DOTALL,
)
_DEVICE_INFO_RE = re.compile(
    r"'DeviceInfo'\s*:\s*(\{.*?\})\s*,\s*\n\s*'DSLiteInfo'",
    re.DOTALL,
)


@dataclass
class ConnectionStatus:
    """Cable modem connection status."""

    cm_status: str
    """Raw CM status string, e.g. OPERATIONAL, RANGING_IN_PROGRESS, ACCESS_DENIED."""

    network_access: bool
    """True if network access is granted."""

    docsis_version: str
    """DOCSIS version string, e.g. '3.1'."""

    @property
    def is_operational(self) -> bool:
        return self.cm_status == "OPERATIONAL"

    @property
    def status_ok(self) -> str:
        """Human-readable OK/NOK string, matching the modem web UI."""
        return "OK" if self.is_operational else "NOK"


@dataclass
class ModemData:
    """All data retrieved from the modem in one call."""

    # --- Connection ---
    cm_status: str
    network_access: bool
    docsis_version: str
    device_mode: str

    # --- Identity ---
    mac_address: str
    serial_number: str
    firmware_version: str
    hardware_version: str

    # --- Time ---
    current_time: datetime | None
    uptime_seconds: int
    uptime_string: str

    # --- Raw ---
    raw: dict[str, Any] = field(repr=False)

    @property
    def connection_status(self) -> ConnectionStatus:
        return ConnectionStatus(
            cm_status=self.cm_status,
            network_access=self.network_access,
            docsis_version=self.docsis_version,
        )

    @property
    def is_operational(self) -> bool:
        return self.cm_status == "OPERATIONAL"


class AuthError(Exception):
    """Raised when login fails."""


class ParseError(Exception):
    """Raised when the modem page cannot be parsed."""


class PyurModemClient:
    """
    Async-compatible HTTP client for the Pyur Compal CH8978E modem.

    Usage::

        client = PyurModemClient("https://192.168.100.1", "admin", "password")
        data = client.fetch()
        print(data.cm_status)        # "OPERATIONAL"
        print(data.firmware_version) # "CH8978E-7.24.310.51-NOSH"

    The session is reused across calls; call :meth:`logout` when done.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        *,
        timeout: int = 15,
        verify_ssl: bool = False,
    ) -> None:
        self._base = host.rstrip("/")
        self._username = username
        self._password = password
        self._timeout = timeout
        self._verify = verify_ssl
        self._session = requests.Session()
        self._logged_in = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def login(self) -> None:
        """Establish a session with the modem.  Raises :class:`AuthError` on failure."""
        # Start from a clean cookie jar so a half-finished earlier login
        # (stale PHPSESSID / CSRF_Token) cannot poison this attempt.
        self._logged_in = False
        self._session.cookies.clear()

        # Step 1: GET root to receive session cookies (PHPSESSID + CSRF_Token)
        self._session.get(
            self._url("/"),
            timeout=self._timeout,
            verify=self._verify,
            allow_redirects=True,
        )

        # Step 2: POST credentials
        csrf = self._session.cookies.get("CSRF_Token", "")
        resp = self._session.post(
            self._url(_PATH_LOGIN),
            data={"username": self._username, "password": self._password},
            headers={
                "Referer": self._url("/common_page/login.php"),
                "CSRF_Token": csrf,
            },
            timeout=self._timeout,
            verify=self._verify,
        )
        resp.raise_for_status()

        try:
            body = resp.json()
        except ValueError as exc:
            raise AuthError(f"Unexpected login response: {resp.text[:200]}") from exc

        if body.get("status") != "success":
            raise AuthError(f"Login failed: {body}")

        self._logged_in = True
        _LOGGER.debug("Logged in (AccessLevel=%s)", body.get("AccessLevel"))

    def fetch(self) -> ModemData:
        """
        Fetch current modem data.  Logs in automatically if not already authenticated.
        """
        if not self._logged_in:
            self.login()

        html = self._get_page(_PATH_WAN_STATUS)
        return _parse_wan_status(html)

    def logout(self) -> None:
        """Invalidate the current session."""
        try:
            self._session.post(
                self._url("/actionHandler/logout.php"),
                timeout=self._timeout,
                verify=self._verify,
            )
        except Exception:  # noqa: BLE001
            pass
        finally:
            self._logged_in = False

    def __enter__(self) -> PyurModemClient:
        self.login()
        return self

    def __exit__(self, *_: object) -> None:
        self.logout()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return self._base + path

    def _get_page(self, path: str) -> str:
        resp = self._session.get(
            self._url(path),
            timeout=self._timeout,
            verify=self._verify,
        )
        resp.raise_for_status()

        # If the session expired the modem returns a redirect to login
        if "login.php" in resp.url or resp.url.endswith("/"):
            _LOGGER.debug("Session expired, re-authenticating")
            self._logged_in = False
            self.login()
            resp = self._session.get(
                self._url(path),
                timeout=self._timeout,
                verify=self._verify,
            )
            resp.raise_for_status()

        return resp.text


# ------------------------------------------------------------------
# Parsing helpers (pure functions, easy to unit-test)
# ------------------------------------------------------------------

def _parse_wan_status(html: str) -> ModemData:
    """Extract :class:`ModemData` from the ``internet_page/RgWanStatus.php`` HTML."""
    m = _DEVICE_INFO_RE.search(html)
    if not m:
        raise ParseError("DeviceInfo block not found in RgWanStatus page")

    try:
        info: dict[str, Any] = json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        raise ParseError(f"Could not parse DeviceInfo JSON: {exc}") from exc

    return ModemData(
        cm_status=info.get("CMStatus", "UNKNOWN"),
        network_access=str(info.get("NetworkAccess", "false")).lower() == "true",
        docsis_version=info.get("DocsisVersion", ""),
        device_mode=info.get("DeviceMode", ""),
        mac_address=info.get("cmMACAddress", ""),
        serial_number=info.get("cmSerialNumber", ""),
        firmware_version=info.get("SwVersion", ""),
        hardware_version=info.get("HwVersion", ""),
        current_time=_parse_time(info.get("CurrentTime")),
        uptime_seconds=_parse_uptime_seconds(info.get("SystemUpTime", [0, ""])),
        uptime_string=_parse_uptime_str(info.get("SystemUpTime", [0, ""])),
        raw=info,
    )


def _parse_time(ct: dict | None) -> datetime | None:
    """Parse the modem's CurrentTime dict into a :class:`datetime`."""
    if not ct:
        return None
    try:
        # Format: {"Y": "2026", "M": "05", "D": "Mon", "time": "11 23:04:27 2026"}
        # Combine into "Mon 11 23:04:27 2026" -> strptime
        date_str = f"{ct['D']} {ct['time']}"
        # Attach UTC so HA's TIMESTAMP sensor accepts the value.
        # The modem does not report a timezone; UTC is used as a safe default.
        return datetime.strptime(date_str, "%a %d %H:%M:%S %Y").replace(tzinfo=UTC)
    except (KeyError, ValueError):
        return None


def _parse_uptime_seconds(uptime: list) -> int:
    """Convert the modem uptime array to total seconds."""
    # Format: [days, "1h: 1m: 45s"]
    try:
        days = int(uptime[0])
        s = str(uptime[1])
        h = int(re.search(r"(\d+)h", s).group(1)) if re.search(r"(\d+)h", s) else 0
        m = int(re.search(r"(\d+)m", s).group(1)) if re.search(r"(\d+)m", s) else 0
        sec = int(re.search(r"(\d+)s", s).group(1)) if re.search(r"(\d+)s", s) else 0
        return int(timedelta(days=days, hours=h, minutes=m, seconds=sec).total_seconds())
    except (IndexError, AttributeError, ValueError):
        return 0


def _parse_uptime_str(uptime: list) -> str:
    """Return a human-readable uptime string."""
    try:
        days = int(uptime[0])
        rest = str(uptime[1]).strip()
        return f"{days} Tage {rest}"
    except (IndexError, ValueError):
        return ""
