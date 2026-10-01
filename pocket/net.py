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


def primary_lan_ip() -> str | None:
    """Best-effort primary LAN IPv4 (UDP connect sends no packets)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("192.0.2.1", 80))
            return sock.getsockname()[0]
        finally:
            sock.close()
    except OSError:
        return None


def all_lan_ips() -> list[str]:
    ips: list[str] = []
    try:
        _, _, addrs = socket.gethostbyname_ex(socket.gethostname())
        ips.extend(a for a in addrs if not a.startswith("127."))
    except OSError:
        pass
    primary = primary_lan_ip()
    if primary and not primary.startswith("127.") and primary not in ips:
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
