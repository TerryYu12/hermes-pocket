# hermes-pocket M2（配对码快捷登录）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 M1「扫码进入登录页」的基础上，交付「配对码快捷登录」：终端 `hermes pocket pair` 生成一次性短码（默认 120 秒有效），手机在仪表盘登录页输入短码即可进入，免输密码。短码一次性、短时效、可撤销、不可重放。

**Architecture:** 复用 hermes-pocket 插件本身作为载体——同一插件现在同时提供 (a) CLI 命令（M1 已有）与 (b) 一个 dashboard-auth provider，后者通过**官方插件 API** `ctx.register_dashboard_auth_provider(provider)` 注册（`hermes_cli/plugins.py`，注册进入进程级 registry，登录页与鉴权门自动发现）。配对码由 CLI 生成并落盘（只存哈希），登录时 provider 校验并核销。Provider 自实现完整 session 生命周期（HMAC 签名 access/refresh），以引擎内置 `plugins/dashboard_auth/basic/` 为参照物。**不改 Hermes core，不新增端口。**

**关键可行性依据（v0.21.5 @ fbf4cbe2 源码核实）：**
- `ctx.register_dashboard_auth_provider(provider)`：官方 ctx 方法（`hermes_cli/plugins.py:766`），upsert 语义、`persistent=True`；注册被"启动作用域"校验（`plugins.py:774`）——插件管理器 scope 必须等于进程 HERMES_HOME scope（default 档正常运行成立）。
- Provider 协议（`hermes_cli/dashboard_auth/base.py:91`）：`name` / `display_name` / `supports_password` / `supports_session`；需覆写 `complete_password_login(*, username, password) -> Session`、`verify_session(*, access_token)`、`refresh_session(*, refresh_token)`、`revoke_session(*, refresh_token)`；`NonInteractiveMixin` 提供登录流无关方法。
- 登录页自动列出所有 `supports_password` provider，各自渲染表单，提交 `{provider, username, password, next}` 到 `/auth/password-login`（`hermes_cli/dashboard_auth/login_page.py:402-410`）。
- `/api/auth/providers` 是公开路径（`public_paths`/middleware 放行），可用于 doctor 检查 provider 是否已注册。

**Non-goal（明确不做）：** 扫二维码全自动登录 / magic-link。公开路径白名单为核心写死（`hermes_cli/dashboard_auth/public_paths.py` + middleware `_GATE_PUBLIC_PREFIXES`），三方插件无法在鉴权门前挂载入口；本 M2 的形态是「扫码 → 登录页 → 输入 8 位短码 → 进入」。

**Tech Stack:** Python ≥3.11；运行时零第三方依赖（stdlib）；pytest；argparse（经 `ctx.register_cli_command`）。

**Spec:** [`docs/design.md`](../../design.md)

## Global Constraints

- 运行时**零第三方依赖**（stdlib + `pocket/vendor/qrcodegen.py`）；`plugin.yaml` 不声明 `python_dependencies`。
- 新增 `.py` 源码保持纯 ASCII；文档可中文。
- **引擎侧 import 必须惰性化**：`hermes_cli.*` 的 import 只允许出现在 `register()` 调用路径内（try/except 包裹），保证 CLI 环境的 `pytest` 与 `hermes pocket qr` 在无引擎依赖时照常工作。
- 每个 Task 结束：测试全绿 → `git add <明确文件>` → commit（`feat|test|docs|chore: ...`）。
- 测试运行：`python -m pytest tests -v`（任意 Python ≥3.11 且带 pytest 的环境；涉及引擎 import 的用例用 `pytest.importorskip` 降级）。
- 版本号只维护 `plugin.yaml` 的 `version`（M2 收尾时 0.1.0 → 0.2.0）。

## 执行模式（编码代理）

- **分工**：编码代理按 Task 施工；维护者编写计划并做验收（`python -m pytest tests -v` + `hermes plugins doctor .` + 读 diff），验收记录写入 `docs/verification/`；**Task 5 的真机扫码需要真实设备配合**。
- 具体派单命令随所在机器而异（运行器路径、代理配置等），由维护者在派单时随任务书提供，不写入本仓库。
- 代理每完成一个 Task 必须按 Global Constraints 提交（`git add` 明确文件 + commit），不 push。

---

## Task 1: 配对码核心（生成 / 校验 / 核销 / 撤销）

**Files:**
- Create: `pocket/pairing.py`
- Test: `tests/test_pairing.py`

**Interfaces（供后续 Task 使用，签名冻结）：**
- `generate_code(length: int = 8) -> str`：从无歧义字母表 `23456789ABCDEFGHJKMNPQRSTVWXYZ`（Crockford 风格，去除 0/1/I/L/O/U）随机生成大写短码。
- `normalize(raw: str) -> str`：大写化 + 去除非字母数字字符（容忍空格/连字符/大小写）。
- `display(code: str) -> str`：`XXXX-XXXX` 分组展示。
- `mint(home: Path | None = None, *, ttl_seconds: int = 120, label: str = "") -> str`：生成并落盘一条配对码，返回明文码（**仅此一次可见**）。
- `validate_and_consume(home: Path | None = None, raw: str = "") -> bool`：校验 + 核销（单次）；恒时比较；过期/已用/不存在一律 False。
- `list_active(home: Path | None = None) -> list[dict]`：未过期未使用的码（字段：`hash` 前 8 位、`created_at`、`expires_at`、`label`）。
- `revoke_all(home: Path | None = None) -> int`：清空全部码，返回条数。
- `store_path(home: Path | None = None) -> Path`：`<HERMES_HOME>/pocket/pair_codes.json`；`home` 为 None 时解析 `HERMES_HOME` 环境变量（再退回 `Path.home() / ".hermes"`）。

**存储格式（文件）：**
```json
{"version": 1, "salt": "<32hex>", "codes": [
  {"hash": "<sha256(salt+normalized) hex>", "created_at": 0.0, "expires_at": 0.0, "used_at": null, "label": ""}
]}
```
- 只存 `sha256(salt + normalize(code))`，不存明文；`salt` 首次创建时生成。
- 落盘一律「临时文件 + `os.replace`」原子替换；目录权限尽力收紧（`chmod 0o700`，Windows 忽略即可）。
- 活跃码上限 3：`mint` 超限时先淘汰最旧。
- 校验用 `hmac.compare_digest` 对全部（上限内）候选做恒时比较。

- [ ] **Step 1: 写 `pocket/pairing.py`**（纯 stdlib；模块 docstring 说明安全模型）
- [ ] **Step 2: 写 `tests/test_pairing.py`**：生成字符集合法；normalize 容忍空格/小写/连字符；mint→validate_and_consume True→二次 False；过期 False（`ttl_seconds=-1` 或注入时钟）；revoke_all 后 False；上限 3 淘汰；文件内不含明文码（读回断言）。
- [ ] **Step 3: 跑测试** → Expected: 全绿。
- [ ] **Step 4: Commit** → `feat: pairing code core (mint/validate/consume/revoke)`

## Task 2: CLI —— `hermes pocket pair` 与 `hermes pocket codes`

**Files:**
- Modify: `pocket/cli.py`（新增两个子命令；复用地址探测与 QR 渲染）
- Test: `tests/test_cli.py`（追加用例）

**Interfaces:**
- `hermes pocket pair [--ttl 120] [--label phone] [--json] [--no-qr]`：
  - mint 一条码；默认同时打印 **二维码**（沿用 `qr` 命令的地址探测 + ASCII 渲染）与**大字短码**：
    ```
    扫描二维码打开面板，然后输入配对码：
        K7M2-9QX4        （有效期 120 秒，一次性）
    ```
  - `--json`：`{"code": "...", "expires_at": ..., "url": "..."}`（供脚本/自动化用）。
  - 无可用局域网地址时降级：仍需打印短码（手机手动开面板用），并提示 `hermes pocket doctor`。
- `hermes pocket codes [--all]`：列出活跃码（hash 前 8 位、剩余秒数、label；`--all` 含已用/过期）；`--revoke` 撤销全部。

- [ ] **Step 1: 实现 pair 子命令**（argv 解析 + 输出；`--json` 走 `json.dumps` 单行）
- [ ] **Step 2: 实现 codes 子命令**
- [ ] **Step 3: 补测试**：monkeypatch `pairing.mint` 固定码断言输出格式；`--json` 字段齐；`codes --revoke` 调用 revoke_all。
- [ ] **Step 4: 跑测试 + 真机外冒烟**（本机 `hermes -p default pocket pair` 目视）→ Commit `feat: pocket pair / codes commands`

## Task 3: Dashboard-auth Provider（核心接线）

**Files:**
- Create: `pocket/auth_provider.py`
- Modify: `__init__.py`（`register(ctx)` 内接线，feature-detect + try/except）
- Test: `tests/test_auth_provider.py`

**Interfaces:**
- `class PocketPairingProvider(NonInteractiveMixin, DashboardAuthProvider)`：
  - `name = "pocket"`；`display_name = "配对码 (Pairing Code)"`；`supports_password = True`。
  - `complete_password_login(*, username: str, password: str) -> Session`：
    - **忽略 username**（登录页字段由核心渲染，不可定制；密码栏即短码栏）。
    - `pairing.validate_and_consume(raw=password)` 成功 → `_mint_session(user_id="pocket")`；失败 → `raise InvalidCredentialsError`。
  - `verify_session` / `refresh_session` / `revoke_session`：**照抄 `plugins/dashboard_auth/basic/__init__.py` 的 `_sign/_unsign/_mint_session/_session` 结构与 TTL 策略**（access 12h / refresh 30d，HMAC-SHA256，kind 区分 access/refresh），secret 来自 `<HERMES_HOME>/pocket/provider_secret`（32 字节 hex，首次自动生成，chmod 0600 尽力）。
  - `register(ctx)`（模块级函数）：`reg = getattr(ctx, "register_dashboard_auth_provider", None)`；不可用（旧引擎）→ 静默返回；可用 → `reg(PocketPairingProvider())`，整体 try/except 兜底，绝不影响 CLI 加载。
- `hermes pocket code` 提供的短码就是给该 provider 的"密码"。

- [ ] **Step 1: 写 `pocket/auth_provider.py`**（引擎 import 全部放在类定义前的函数体内/惰性——见 Global Constraints；核心逻辑（token 签名工具）写成模块内纯函数便于测试）
- [ ] **Step 2: 接线 `__init__.py`**：`register(ctx)` 里先 `pocket_cli.register(ctx)`，再 try `auth_provider.register(ctx)`。
- [ ] **Step 3: 写测试**：
  - `pytest.importorskip("hermes_cli.dashboard_auth.base")`——有引擎环境时：协议合规（`assert_protocol_compliance`）、短码命中/失配/过期路径、`_sign/_unsign` 回环、refresh 轮换。
  - 无引擎环境时自动跳过，且 `tests/test_manifest.py`、CLI 用例保持全绿（证明惰性 import 成立）。
- [ ] **Step 4: 跑测试** → Commit `feat: pocket pairing auth provider`

## Task 4: Doctor 检查 + 文档

**Files:**
- Modify: `pocket/probe.py`、`pocket/cli.py`（doctor 追加检查项）
- Modify: `README.md`、`docs/design.md`

**Interfaces:**
- `check_dashboard_auth_provider(port: int = 9119) -> Check`：GET `http://127.0.0.1:{port}/api/auth/providers`（公开路径），断言列表含 `"pocket"`；缺失时 fix 提示 = 「安装/启用 hermes-pocket 插件后重启 dashboard」。
- README 新增「配对码登录」一节（三步：`hermes pocket pair` → 扫码 → 输码）；`docs/design.md` 增补 M2 决策记录（含 Non-goal 与公开路径结论）。

- [ ] **Step 1: 实现检查项** + 测试（mock URL）
- [ ] **Step 2: 文档更新**
- [ ] **Step 3: Commit** `feat: doctor check + docs for pairing login`

## Task 5: 端到端验收（维护者执行）

- [ ] 本机：安装/更新插件 → 重启 dashboard → `hermes pocket pair` 生成码 → `curl -X POST http://127.0.0.1:9119/auth/password-login -d '{"provider":"pocket","username":"","password":"<码>","next":"/"}'` → 断言 200 + Set-Cookie → 带 cookie 请求 `/api/status` 200。
- [ ] 负例：同码二次提交被拒；过期码被拒。
- [ ] 真机：扫码 → 登录页选择/呈现「配对码」表单 → 输入短码 → 进入面板（对照 M1 验收记录格式）。
- [ ] `plugin.yaml` 版本 0.1.0 → 0.2.0；验收记录 `docs/verification/` 落盘；README 状态更新。
- [ ] Commit `docs: m2 acceptance record`

---

## Risks & Notes

- **作用域约束**：注册被 `plugins.py:774` 的启动作用域校验——第三方 provider 只对"启动进程的 HERMES_HOME 档"生效；多档 dashboard 场景下其它档看不到该 provider（文档如实说明）。
- **引擎版本漂移**：本计划基于 v0.21.5 @ fbf4cbe2 核实；实现时以**当前安装**的 `hermes_cli/plugins.py` / `dashboard_auth/base.py` 为准，全部 API 均 feature-detect + 降级。
- **短码安全参数**：8 字符 × 32 字母表 ≈ 40 bit；TTL 120s、单次使用、活跃上限 3、恒时比较、只存哈希、不落日志——配合登录路由自带限速，穷举不可行。
- **登录页呈现**：登录页会同时列出「Username & Password」与「配对码」两个表单；这是核心行为，无需也无法改；README 里给出识别指引（手机端选"配对码"那个）。
- **不 push**：编码代理只 commit；推送与发布由维护者完成。
