"""Remote-access prerequisite checks for `hermes pocket doctor`. Stdlib only."""
from __future__ import annotations

import json
import os
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Check:
    name: str
    status: str  # "ok" | "warn" | "fail" | "info"
    detail: str
    fix: str = ""


def _http_json(url: str, timeout: float = 3.0) -> dict | None:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "hermes-pocket-doctor/0.1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (localhost only)
            return json.loads(response.read(65536).decode("utf-8", "replace"))
    except Exception:
        return None


def check_api_server(port: int = 8642) -> Check:
    data = _http_json(f"http://127.0.0.1:{port}/health")
    if data and data.get("status") == "ok":
        return Check("API server", "ok", f"127.0.0.1:{port} reachable (version {data.get('version', '?')})")
    return Check(
        "API server",
        "fail",
        f"127.0.0.1:{port} unreachable",
        "Set API_SERVER_ENABLED=true and API_SERVER_KEY in .env, then restart the gateway",
    )


def check_dashboard(port: int = 9119) -> Check:
    data = _http_json(f"http://127.0.0.1:{port}/api/status")
    if data is None:
        return Check("Dashboard", "fail", f"127.0.0.1:{port} unreachable", "Start it: hermes dashboard")
    if data.get("auth_required"):
        providers = ", ".join(data.get("auth_providers") or ["?"])
        return Check("Dashboard", "ok", f"running; auth gate on (providers: {providers})")
    return Check(
        "Dashboard",
        "warn",
        "running without auth (loopback-only bind)",
        "For remote access bind 0.0.0.0 and configure dashboard auth (basic_auth or OAuth)",
    )


def check_tailscale() -> Check:
    exe = shutil.which("tailscale")
    if not exe:
        return Check("Tailscale", "info", "not installed (optional)", "Install on PC + phone for zero-public-exposure access")
    return Check("Tailscale", "ok", f"found: {exe}")


def check_cloudflared() -> Check:
    exe = shutil.which("cloudflared")
    if not exe:
        return Check("cloudflared", "info", "not installed (optional)", "Only needed for the public-tunnel scenario (requires CF Access)")
    return Check("cloudflared", "ok", f"found: {exe}")


def check_env() -> Check:
    home = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")
    env_path = Path(home) / ".env"
    if not env_path.exists():
        return Check("HERMES_HOME/.env", "warn", f"not found: {env_path}", "Set HERMES_HOME or create the .env file")
    text = env_path.read_text(encoding="utf-8", errors="replace")
    enabled = "API_SERVER_ENABLED=true" in text.replace(" ", "")
    if enabled:
        return Check("HERMES_HOME/.env", "ok", "API_SERVER_ENABLED=true present")
    return Check(
        "HERMES_HOME/.env",
        "warn",
        "API_SERVER_ENABLED=true not found",
        "Add it (plus API_SERVER_KEY) to enable the API server",
    )


def run_all(dashboard_port: int = 9119, api_port: int = 8642) -> list[Check]:
    return [
        check_env(),
        check_api_server(api_port),
        check_dashboard(dashboard_port),
        check_tailscale(),
        check_cloudflared(),
    ]
