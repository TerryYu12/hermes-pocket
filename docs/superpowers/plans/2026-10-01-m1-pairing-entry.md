# hermes-pocket M1（配对入口 MVP）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付 `hermes pocket qr` 与 `hermes pocket doctor`：在终端生成指向自部署 Hermes dashboard 的配对二维码（ASCII + PNG），并检查远端访问前置条件；插件可被 `hermes plugins install` 安装。

**Architecture:** 纯 CLI 插件（`plugin.yaml` + `register(ctx)` + `pocket/` 包）。零第三方运行时依赖：QR 编码 vendored 自 Project Nayuki `qrcodegen`（MIT），ASCII/PNG 渲染与地址探测全部标准库自实现。不新增端口、不改 Hermes core。

**Tech Stack:** Python ≥3.11（平台强制，论证见 `docs/design.md` §1.5）；pytest；argparse（经 `ctx.register_cli_command`）。

**Spec:** [`docs/design.md`](../../design.md)

## Global Constraints

- 运行时**零第三方依赖**（stdlib + `pocket/vendor/qrcodegen.py`）；`plugin.yaml` 不声明 `python_dependencies`。
- 新增 `.py` 源码保持纯 ASCII；文档可中文。
- 每个 Task 结束：测试全绿 → `git add <明确文件>` → commit（`feat|test|docs|chore: ...`）。
- 测试运行：`python -m pytest tests -v`（任意 Python ≥3.11 且带 pytest 的环境）。
- 版本号只维护 `plugin.yaml` 的 `version`。

## 执行模式（编码代理）

- **分工**：编码代理按 Task 施工；维护者编写计划并做验收（`python -m pytest tests -v` + `hermes plugins doctor .` + 读 diff），验收记录写入 `docs/verification/`；**Task 7 的真机扫码需要真实设备配合**。
- 具体派单命令随所在机器而异（运行器路径、代理配置等），由维护者在派单时随任务书提供，不写入本仓库。
- 代理每完成一个 Task 必须按 Global Constraints 提交（`git add` 明确文件 + commit），不 push。

---

## Task 1: 仓库骨架 + 插件清单

**Files:**
- Create: `plugin.yaml`、`__init__.py`、`pocket/__init__.py`、`tests/__init__.py`、`tests/conftest.py`
- Test: `tests/test_manifest.py`

**Interfaces:**
- Produces: `pocket` 包；`register(ctx)` 入口（Task 4 在其内部接入 CLI）。

- [ ] **Step 1: 写 `plugin.yaml`**

```yaml
name: hermes-pocket
version: 0.1.0
description: "Scan, open, chat — pairing QR and remote-access checks for bringing your self-hosted Hermes to a phone. No cloud relay, no telemetry."
author: "TerryYu12"
```

- [ ] **Step 2: 写最小入口与包**

`__init__.py`（Task 4 会替换其函数体）：

```python
"""hermes-pocket plugin entry point."""
from __future__ import annotations


def register(ctx) -> None:
    """Called by the Hermes plugin loader (CLI wiring lands in Task 4)."""
    return None
```

`pocket/__init__.py`：

```python
"""hermes-pocket core package."""
```

`tests/__init__.py`：空文件。

`tests/conftest.py`：

```python
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
```

- [ ] **Step 3: 写 `tests/test_manifest.py`**

```python
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_manifest_fields():
    text = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
    assert "name: hermes-pocket" in text
    assert "version:" in text
    assert "description:" in text
    assert "author:" in text


def test_register_entrypoint_exists():
    spec = importlib.util.spec_from_file_location("hermes_pocket_entry", ROOT / "__init__.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(getattr(mod, "register", None))
```

- [ ] **Step 4: 跑测试** → Expected: `2 passed`。
- [ ] **Step 5: Hermes 侧体检（人工）**

```bash
hermes plugins doctor .
```

Expected: 无 ERROR 级问题（此阶段无工具/无 CLI，出现"提示级"信息属正常；若报 `no register() function` 之类硬错误，先记录，Task 4 完成后复验）。

- [ ] **Step 6: Commit**

```bash
git add plugin.yaml __init__.py pocket/__init__.py tests/__init__.py tests/conftest.py tests/test_manifest.py
git commit -m "feat: plugin scaffold and manifest"
```

## Task 2: QR 渲染（vendored qrcodegen + ASCII/PNG）

**Files:**
- Create: `pocket/vendor/__init__.py`、`pocket/vendor/qrcodegen.py`（拉取）、`pocket/vendor/README.txt`、`pocket/qr.py`
- Test: `tests/test_qr.py`

**Interfaces:**
- Produces: `pocket.qr.make_matrix(text) -> list[list[bool]]`、`pocket.qr.render_ascii(matrix, quiet=2, invert=False) -> str`、`pocket.qr.render_png(matrix, scale=8, quiet=4, invert=False) -> bytes`（Task 4 使用）。

- [ ] **Step 1: vendor 拉取 + 记录来源**

```bash
cd <repo-root>
mkdir -p pocket/vendor
curl -fsSL -o pocket/vendor/qrcodegen.py \
  https://raw.githubusercontent.com/nayuki/QR-Code-generator/master/python/qrcodegen.py
sha256sum pocket/vendor/qrcodegen.py
```
`pocket/vendor/__init__.py` 置空；`pocket/vendor/README.txt` 写入：来源 URL、获取日期、上一步的 sha256、"MIT License, Copyright (c) Project Nayuki；保留原文件许可头；升级=重拉并比对 sha256"。

- [ ] **Step 2: 验证 vendor 可用**

```bash
python -c "from pocket.vendor.qrcodegen import QrCode; q=QrCode.encode_text('https://example.com', QrCode.Ecc.MEDIUM); print('size', q.get_size())"
```
Expected: 打印 `size <N>`（N≥21），无异常。

- [ ] **Step 3: 写 `pocket/qr.py`**

```python
"""QR generation (vendored qrcodegen) plus ASCII / PNG rendering. Stdlib only."""
from __future__ import annotations

import struct
import zlib

from .vendor.qrcodegen import QrCode


def make_matrix(text: str) -> list[list[bool]]:
    """Encode text into a QR matrix (list of rows of bool; True = dark module)."""
    qr = QrCode.encode_text(text, QrCode.Ecc.MEDIUM)
    n = qr.get_size()
    return [[qr.get_module(x, y) for x in range(n)] for y in range(n)]


def render_ascii(matrix: list[list[bool]], quiet: int = 2, invert: bool = False) -> str:
    """Render as half-block characters (two vertical modules per text row)."""
    n = len(matrix)
    total = n + 2 * quiet

    def dark(x: int, y: int) -> bool:
        inside = quiet <= x < quiet + n and quiet <= y < quiet + n
        value = bool(inside and matrix[y - quiet][x - quiet])
        return (not value) if invert else value

    lines: list[str] = []
    y = 0
    while y < total:
        row: list[str] = []
        for x in range(total):
            top = dark(x, y)
            bottom = dark(x, y + 1) if y + 1 < total else False
            if top and bottom:
                row.append("\u2588")  # full block
            elif top:
                row.append("\u2580")  # upper half
            elif bottom:
                row.append("\u2584")  # lower half
            else:
                row.append(" ")
        lines.append("".join(row))
        y += 2
    return "\n".join(lines)


def render_png(matrix: list[list[bool]], scale: int = 8, quiet: int = 4, invert: bool = False) -> bytes:
    """Render as an 8-bit grayscale PNG (dark modules black), stdlib only."""
    n = len(matrix)
    side = (n + 2 * quiet) * scale
    raw = bytearray()
    for y in range(side):
        raw.append(0)  # filter type: None
        my = y // scale - quiet
        for x in range(side):
            mx = x // scale - quiet
            dark = 0 <= mx < n and 0 <= my < n and matrix[my][mx]
            if invert:
                dark = not dark
            raw.append(0 if dark else 255)
    ihdr = struct.pack(">IIBBBBB", side, side, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )
```

- [ ] **Step 4: 写 `tests/test_qr.py`**

```python
import struct

from pocket.qr import make_matrix, render_ascii, render_png


def test_matrix_is_square():
    matrix = make_matrix("https://example.com")
    n = len(matrix)
    assert n >= 21
    assert all(len(row) == n for row in matrix)


def test_ascii_shape_and_blocks():
    matrix = make_matrix("hi")
    text = render_ascii(matrix, quiet=2)
    lines = text.splitlines()
    assert len(lines) == (len(matrix) + 4 + 1) // 2
    assert max(len(line) for line in lines) == len(matrix) + 4
    assert "\u2588" in text


def test_png_header_and_size():
    matrix = make_matrix("hi")
    raw = render_png(matrix, scale=4, quiet=2)
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", raw[16:24])
    side = (len(matrix) + 4) * 4
    assert (width, height) == (side, side)
```

- [ ] **Step 5: 跑测试** → Expected: `3 passed`。
- [ ] **Step 6: Commit**

```bash
git add pocket/vendor/ pocket/qr.py tests/test_qr.py
git commit -m "feat: QR rendering (ascii + png) with vendored qrcodegen"
```

## Task 3: 地址探测 `pocket/net.py`

**Files:**
- Create: `pocket/net.py`
- Test: `tests/test_net.py`

**Interfaces:**
- Produces: `pocket.net.Candidate(url, kind, note)`、`pocket.net.detect_candidates(port, scheme="http", custom=None) -> list[Candidate]`（Task 4 使用）。

- [ ] **Step 1: 写 `pocket/net.py`**

```python
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
```

- [ ] **Step 2: 写 `tests/test_net.py`**

```python
from pocket import net


def test_custom_wins():
    cands = net.detect_candidates(9119, custom="https://x.example")
    assert len(cands) == 1
    assert cands[0].url == "https://x.example"
    assert cands[0].kind == "custom"


def test_lan_and_tailscale_listed(monkeypatch):
    monkeypatch.setattr(net, "all_lan_ips", lambda: ["192.168.1.3"])
    monkeypatch.setattr(net, "tailscale_ip", lambda: "100.64.0.9")
    urls = [c.url for c in net.detect_candidates(9119)]
    assert "http://192.168.1.3:9119" in urls
    assert "http://100.64.0.9:9119" in urls


def test_no_tailscale(monkeypatch):
    monkeypatch.setattr(net, "all_lan_ips", lambda: ["10.0.0.5"])
    monkeypatch.setattr(net, "tailscale_ip", lambda: None)
    cands = net.detect_candidates(9119)
    assert [c.kind for c in cands] == ["lan"]
```

- [ ] **Step 3: 跑测试** → Expected: `3 passed`。
- [ ] **Step 4: Commit**

```bash
git add pocket/net.py tests/test_net.py
git commit -m "feat: reachable-address detection (lan / tailscale / custom)"
```

## Task 4: CLI 接线（`hermes pocket qr`）

**Files:**
- Create: `pocket/cli.py`
- Modify: `__init__.py`（register 内接入）
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `pocket.net.detect_candidates`、`pocket.qr.*`（Task 2/3）。
- Produces: `pocket.cli.register(ctx)`；`pocket.cli.setup(parser)`；`pocket.cli.handle(args) -> int`。

- [ ] **Step 1: 写 `tests/test_cli.py`（先失败）**

```python
import argparse

from pocket import cli


def _ns(**over):
    ns = argparse.Namespace(
        port=9119, url=None, png=None, select=0, invert=False, list_only=False
    )
    for key, value in over.items():
        setattr(ns, key, value)
    return ns


def test_qr_lists_and_renders(monkeypatch, capsys):
    monkeypatch.setattr(
        cli.net,
        "detect_candidates",
        lambda port, scheme="http", custom=None: [
            cli.net.Candidate("http://192.168.1.3:9119", "lan", "LAN")
        ],
    )
    assert cli._handle_qr(_ns()) == 0
    out = capsys.readouterr().out
    assert "http://192.168.1.3:9119" in out
    assert "\u2588" in out


def test_qr_custom_and_png(tmp_path):
    out_png = tmp_path / "qr.png"
    code = cli._handle_qr(_ns(url="https://x.example", png=str(out_png)))
    assert code == 0
    assert out_png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_qr_list_only(monkeypatch, capsys):
    monkeypatch.setattr(
        cli.net,
        "detect_candidates",
        lambda port, scheme="http", custom=None: [
            cli.net.Candidate("http://a:9119", "lan", "LAN")
        ],
    )
    assert cli._handle_qr(_ns(list_only=True)) == 0
    out = capsys.readouterr().out
    assert "http://a:9119" in out
```

Run: `pytest tests/test_cli.py -v` → Expected: FAIL（`No module named 'pocket.cli'`）。

- [ ] **Step 2: 写 `pocket/cli.py`**

```python
"""``hermes pocket ...`` CLI subcommands."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import net, qr


def register(ctx) -> None:
    ctx.register_cli_command(
        name="pocket",
        help="Hermes Pocket: pairing QR + remote-access checks for your phone",
        setup_fn=setup,
        handler_fn=handle,
    )


def setup(parser: argparse.ArgumentParser) -> None:
    subs = parser.add_subparsers(dest="pocket_command", required=False)
    p_qr = subs.add_parser("qr", help="Print a pairing QR (terminal) and optionally save a PNG")
    p_qr.add_argument("--url", default=None, help="Override the URL to encode (e.g. https://hermes.example.com)")
    p_qr.add_argument("--port", type=int, default=9119, help="Dashboard port to embed (default 9119)")
    p_qr.add_argument("--png", default=None, help="Also save a PNG to this path")
    p_qr.add_argument("--select", type=int, default=0, help="Which candidate to render (index, default 0)")
    p_qr.add_argument("--invert", action="store_true", help="Invert colors (for dark terminals)")
    p_qr.add_argument("--list", action="store_true", dest="list_only", help="Only list candidate URLs")
    p_qr.set_defaults(pocket_handler=_handle_qr)


def handle(args: argparse.Namespace) -> int:
    handler = getattr(args, "pocket_handler", None)
    if handler is None:
        print("usage: hermes pocket {qr} ...", file=sys.stderr)
        return 2
    return handler(args)


def _handle_qr(args: argparse.Namespace) -> int:
    cands = net.detect_candidates(args.port, custom=args.url)
    if not cands:
        print("No reachable address candidate found. Use --url to specify one.", file=sys.stderr)
        return 1
    for index, cand in enumerate(cands):
        print(f"[{index}] {cand.url}  ({cand.kind})")
    if args.list_only:
        return 0
    if not 0 <= args.select < len(cands):
        print(f"--select {args.select} out of range (0..{len(cands) - 1})", file=sys.stderr)
        return 2
    target = cands[args.select].url
    print()
    print(qr.render_ascii(qr.make_matrix(target), invert=args.invert))
    print(f"\n-> {target}")
    if args.png:
        out = Path(args.png).expanduser()
        out.write_bytes(qr.render_png(qr.make_matrix(target), invert=args.invert))
        print(f"PNG saved: {out}")
    return 0
```

- [ ] **Step 3: 跑测试** → Expected: `3 passed`。

- [ ] **Step 4: 接入入口 —— 修改 `__init__.py` 的 register 函数体**

```python
def register(ctx) -> None:
    """Called by the Hermes plugin loader."""
    from .pocket import cli as pocket_cli

    pocket_cli.register(ctx)
```

- [ ] **Step 5: 全量测试** → `pytest tests -v` Expected: 全部通过（8 passed）。
- [ ] **Step 6: Commit**

```bash
git add pocket/cli.py __init__.py tests/test_cli.py
git commit -m "feat: hermes pocket qr command"
```

## Task 5: `hermes pocket doctor`

**Files:**
- Create: `pocket/probe.py`
- Modify: `pocket/cli.py`（注册 doctor 子命令）
- Test: `tests/test_probe.py`、`tests/test_cli.py`（追加 doctor 用例）

**Interfaces:**
- Produces: `pocket.probe.Check(name, status, detail, fix)`、`pocket.probe.run_all(dashboard_port=9119, api_port=8642) -> list[Check]`。

- [ ] **Step 1: 写 `pocket/probe.py`**

```python
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
```

- [ ] **Step 2: 写 `tests/test_probe.py`**

```python
from pocket import probe


def test_api_ok(monkeypatch):
    monkeypatch.setattr(probe, "_http_json", lambda url, timeout=3.0: {"status": "ok", "version": "1.2.3"})
    assert probe.check_api_server().status == "ok"


def test_api_down(monkeypatch):
    monkeypatch.setattr(probe, "_http_json", lambda url, timeout=3.0: None)
    check = probe.check_api_server()
    assert check.status == "fail"
    assert check.fix


def test_dashboard_gate_warn(monkeypatch):
    monkeypatch.setattr(
        probe, "_http_json", lambda url, timeout=3.0: {"auth_required": False, "auth_providers": []}
    )
    assert probe.check_dashboard().status == "warn"


def test_env_check(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / ".env").write_text("API_SERVER_ENABLED=true\n", encoding="utf-8")
    assert probe.check_env().status == "ok"
```

- [ ] **Step 3: cli.py 注册 doctor 子命令**（在 `setup()` 里追加）

```python
    p_doc = subs.add_parser("doctor", help="Check remote-access prerequisites and print fixes")
    p_doc.set_defaults(pocket_handler=_handle_doctor)
```

同文件追加：

```python
_SYM = {"ok": "\u2713", "warn": "!", "fail": "\u2717", "info": "i"}


def _handle_doctor(args: argparse.Namespace) -> int:
    from . import probe

    checks = probe.run_all()
    for check in checks:
        print(f"[{_SYM.get(check.status, '?')}] {check.name}: {check.detail}")
        if check.fix and check.status in ("warn", "fail"):
            print(f"    -> {check.fix}")
    return 0 if all(c.status != "fail" for c in checks) else 1
```

- [ ] **Step 4: 追加 `tests/test_cli.py` 用例**

```python
def test_doctor_handler(monkeypatch, capsys):
    from pocket import cli, probe

    monkeypatch.setattr(
        probe, "run_all", lambda: [probe.Check("API server", "ok", "reachable")]
    )
    assert cli._handle_doctor(argparse.Namespace()) == 0
    out = capsys.readouterr().out
    assert "API server" in out


def test_doctor_fail_exit(monkeypatch):
    from pocket import cli, probe

    monkeypatch.setattr(
        probe, "run_all", lambda: [probe.Check("API server", "fail", "down", "fix it")]
    )
    assert cli._handle_doctor(argparse.Namespace()) == 1
```

- [ ] **Step 5: 跑全量测试** → Expected: 全部通过。
- [ ] **Step 6: Commit**

```bash
git add pocket/probe.py pocket/cli.py tests/test_probe.py tests/test_cli.py
git commit -m "feat: hermes pocket doctor"
```

## Task 6: 三链路文档 + README 完善

**Files:**
- Create: `docs/lan.md`、`docs/tailscale.md`、`docs/cloudflare.md`
- Modify: `README.md`

内容要求（每篇含：适用场景 / 前置条件 / 步骤 / 验证 / 排错）：

- `docs/lan.md`：前置=API server 已启用 + dashboard 绑定 `0.0.0.0` 且配置认证；步骤=`hermes pocket doctor` → `hermes pocket qr` → 手机同 Wi-Fi 扫码；排错=防火墙、AP 隔离、手机 VPN 关闭。
- `docs/tailscale.md`：推荐路径（零公网暴露）。前置=PC 与手机装 Tailscale 并登录同一账号；步骤=`tailscale ip -4` → `hermes pocket qr`（自动出现 tailscale 候选）；注意=安卓 VPN 槽位互斥、PC 上 Clash TUN 共存观察、headscale 亦兼容。
- `docs/cloudflare.md`：**仅进阶**。前置=**必须**配置 Cloudflare Access（不然别上公网）；给出 cloudflared 隧道到 `127.0.0.1:9119` 的示例 + dashboard 反代注意项（trusted_proxies/public_url）；引用官方口径：basic 密码仅限受信网络/VPN。
- `README.md`：补"快速上手"（3 条命令）+ 文档索引。

- [ ] **Step 1: 写三篇文档 → Step 2: 更新 README → Step 3: Commit**

```bash
git add docs/lan.md docs/tailscale.md docs/cloudflare.md README.md
git commit -m "docs: m1 setup guides (lan / tailscale / cloudflare) + readme quickstart"
```

## Task 7: 本地安装 + 真机验收（需用户配合）

- [ ] **Step 1: 安装本地插件（两种方式，以成功者为准）**

```bash
hermes plugins install "file://<path-to-repo>" --enable
# 失败则：
hermes plugins install "<path-to-repo>" --enable
```

- [ ] **Step 2: 确认已启用**

```bash
hermes plugins list
```
Expected: `hermes-pocket` 出现在列表且为 enabled（第三方插件默认 opt-in，--enable 负责这一步）。

- [ ] **Step 3: 体检 + 修复**

```bash
hermes pocket doctor
```
按输出修复：预期 API server ✓；dashboard 未运行则先起 `hermes dashboard --host 0.0.0.0 --port 9119`（并配置认证）。

- [ ] **Step 4: 生成二维码 + 真机扫码（用户操作）**

```bash
hermes pocket qr
```
手机连同一 Wi-Fi → 扫码 → 登录 → 打开会话 → 发一条消息得到回复。

- [ ] **Step 5: 写验收记录 → Step 6: Commit**

`docs/verification/2026-10-01-m1.md`：环境、命令、实际输出、真机结果、遗留问题。
```bash
git add docs/verification/2026-10-01-m1.md
git commit -m "docs: m1 acceptance record"
```

---

## Self-Review（已完成）

- **Spec 覆盖**：design.md 的 M1 交付物（qr / doctor / 三文档 / 真机验收）→ Task 2–7；脚手架与清单 → Task 1；技术栈约束 → Global Constraints。
- **占位符扫描**：无 TBD/TODO；vendored 文件为"拉取步骤 + sha256 记录"（可复现）。
- **类型/命名一致**：`Candidate` / `_handle_qr` / `_handle_doctor` / `Check` 跨任务一致；`pocket_handler` 分发机制在 Task 4 定义、Task 5 复用。

## Execution Handoff

计划就绪后：逐 Task 派给编码代理 → 每段完成后由维护者验收（`python -m pytest tests -v` + `hermes plugins doctor .` + diff 审读）→ 依次推进；Task 7 由真实设备参与验收。
