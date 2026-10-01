"""Reachable-address detection for pairing URLs. Stdlib only."""
from __future__ import annotations

import shutil
import socket
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    url: str
    kind: str  # "lan" | "tailscale" | "custom"
    note: str = ""


_VIRTUAL_PREFIXES = ("127.", "169.254.", "198.18.", "198.19.")


def _is_useful_lan_ip(ip: str) -> bool:
    """False for loopback / link-local / RFC 2544 benchmark ranges (Clash TUN etc.)."""
    return not ip.startswith(_VIRTUAL_PREFIXES)


def primary_lan_ip() -> str | None:
    """Best-effort primary LAN IPv4 (UDP connect sends no packets)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("192.0.2.1", 80))
            ip = sock.getsockname()[0]
        finally:
            sock.close()
    except OSError:
        return None
    return ip if _is_useful_lan_ip(ip) else None


def all_lan_ips() -> list[str]:
    ips: list[str] = []
    try:
        _, _, addrs = socket.gethostbyname_ex(socket.gethostname())
        ips.extend(a for a in addrs if _is_useful_lan_ip(a))
    except OSError:
        pass
    primary = primary_lan_ip()
    if primary and _is_useful_lan_ip(primary) and primary not in ips:
        ips.insert(0, primary)
    return ips


def tailscale_ip() -> str | None:
    exe = shutil.which("tailscale")
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, "ip", "-4"], capture_output=True, text=True, timeout=5
        )
        lines = (proc.stdout or "").strip().splitlines()
        if proc.returncode == 0 and lines:
            return lines[0].strip()
    except (OSError, subprocess.TimeoutExpired):
        return None
    return None


def detect_candidates(
    port: int, scheme: str = "http", custom: str | None = None
) -> list[Candidate]:
    if custom:
        return [Candidate(custom, "custom", "user-specified")]
    out: list[Candidate] = []
    for ip in all_lan_ips():
        out.append(Candidate(f"{scheme}://{ip}:{port}", "lan", "LAN"))
    ts = tailscale_ip()
    if ts:
        out.append(Candidate(f"{scheme}://{ts}:{port}", "tailscale", "Tailscale"))
    return out
