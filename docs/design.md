# hermes-pocket：Hermes 手机远控开源插件 —— 设计方案 v1.0

> **状态**：已定稿（名称 hermes-pocket / MIT / 公开开发）｜ **日期**：2026-10-01 ｜ **作者**：维护者
> **实施计划**：`docs/superpowers/plans/2026-10-01-m1-pairing-entry.md`（M1）
> **关联调研**：ZCode「Web Remote Control」开源实现调研（结论摘要见 §1.2）

---

## 0. 一句话

做一个开源 Hermes 插件 **hermes-pocket**：`hermes pocket qr` 生成二维码 → 手机扫码（或输密码）→ 打开移动友好的「口袋页」→ 从任何网络安全地接着用家里的 Hermes。
**核心取舍：不建云端 relay——复用你 24h 常驻的 Hermes 网关当"中转"。**

## 1. 背景

### 1.1 需求
- 远程安卓连 Hermes：扫码打开网页（zcode 式）或密码连接均可；
- 出口是**开源项目**，形态为 **Hermes 插件**（`hermes plugins install` 一键装）；
- 安全敏感：不引入云中转、不引入遥测。

### 1.2 zcode 调研结论（M0，摘要）
- zcode 的扫码远控主干（扫码 + 云端 relay + 配对 token）**未开源**；OSS 只剩 UI 壳、协议语义与环回 WS。
- 可搬：配对状态机设计（register→persisted→paired + challenge/response）、`web-remote-replayable` 重连恢复语义、两个小函数（手机指纹 / 二维码渲染）。
- **最值钱结论**：扫码远控的服务端本质 = 一台 24h 在线的配对/转发服务——而 Hermes 用户本来就有（常驻网关）。**不需要自建公网 relay，用既有网关即可。**

### 1.3 Hermes 插件能力（已核实，2026-10-01）
| 能力 | 结论 | 依据 |
|---|---|---|
| 注册 CLI 子命令 | ✅ `register_cli_command(name, help, setup_fn, handler_fn)` → `hermes <name> …` | `hermes_cli/plugins.py` |
| 注册 dashboard 认证 provider | ✅ `ctx.register_dashboard_auth_provider()`，官方文档列为插件扩展点 | Web Dashboard docs「Custom providers」 |
| Dashboard UI 扩展 | ✅ `manifest.json` + 预构建 JS bundle，可注册 tab / 槽位，运行时 drop-in | docs「Extending the Dashboard」 |
| Dashboard 后端路由 | ✅ `plugin_api.py`（FastAPI router）挂载于 `/api/plugins/<name>/` | 同上；先例 `plugins/kanban/dashboard/` |
| 安装与治理 | `hermes plugins install owner/repo --enable`；第三方默认 opt-in；安装时安全扫描 | plugins docs / CLI |
| 插件入口 | `register(ctx)`（loader 按名调用） | `hermes_cli/plugins_loader.py` |

结论：**本插件零 core 改动，全部能力已存在。**

### 1.4 差异化定位
| 方案 | 形态 | 安装 | 链路 | 中转 |
|---|---|---|---|---|
| Conduit（cogwheel0） | 原生 App | 装 App | 自备 | 无 |
| 社区安卓端（rusty4444 / Hy4ri 等） | 原生 App | 装 App | LAN/Tailscale | 无 |
| 官方 mobile pairing（#103766） | 官方配对 | 未发布 | .ts.net | 无 |
| Codename-11/hermes-relay | 托管中继 | — | 云 | ✅ |
| **hermes-pocket（本项目）** | **网页/PWA + 插件** | **`plugins install`** | **LAN/Tailscale/CF** | **无** |

### 1.5 技术栈选型（论证）

**结论：插件主干 = Python（平台强制）；界面 = 原生 JS（M2）；运行时零第三方依赖；代码施工交给编码代理。**

| 部件 | 选型 | 理由 / 备选否决 |
|---|---|---|
| 插件主干（CLI / doctor / M2 provider） | **Python** | Hermes 插件 SDK 就是 Python：`register(ctx)`、`register_cli_command()`、`register_dashboard_auth_provider()` 均为 Python API（已核实源码 `hermes_cli/plugins.py` / `plugins_loader.py`）。用 Go/Rust/Node 写独立进程会失去 `hermes plugins install` 一体化与全部 SDK 能力 → 否决 |
| Dashboard 界面（M2） | **原生 JS 单文件 bundle**（复杂度上来再考虑 Vite+React） | 官方 UI 插件 = `manifest.json` + **预构建** JS，用户侧免构建；M2 只做"看会话 + 聊"最小页，先不上框架 |
| QR 编码 | **vendored `qrcodegen.py`**（Project Nayuki，MIT，单文件纯 Python） | 零依赖、离线可用；不用 `qrcode` 包（会引入依赖 consent 摩擦） |
| ASCII / PNG 渲染 | 标准库自实现（半块字符渲染；`zlib`+`struct` 手写 PNG） | 无依赖、可控可测 |
| 测试 | **pytest**（断言仅用标准库） | 不依赖 yaml 等第三方；任意 ≥3.11 且带 pytest 的环境均可运行 |
| 目标运行环境 | **Python ≥3.11**（兼容 3.11–3.14） | Hermes 运行时覆盖 3.11–3.14；避免 3.12+ 专有语法 |
| 编码约束 | 源码纯 ASCII（注释英文）；文档中文 | 跨平台编码安全（避免 ANSI/GBK 解码事故） |
| 代码施工 | 编码代理（Claude Code / Pi Coding Agent 等） | 维护者写计划与验收，编码交代理执行；派单细节因机器而异、不入库 |

**明确不作为**：用户侧零构建步骤；零网络调用；零框架级运行依赖；不引包管理器依赖链。

## 2. 产品定义

### 2.1 用户故事
- **A 在家**：`hermes pocket qr` → 手机 Wi-Fi 扫码 → 输一次密码 → 见会话 → 聊。
- **B 在外**：同 A，链路换 Tailscale（推荐）或 CF 隧道。
- **C 新设备**：扫码 + 一次性短命配对码直登（M2），用完即焚。
- **D PWA**：页面上「添加到主屏幕」，图标即开。

### 2.2 非目标（v1 明确不做）
- ❌ 云端 relay / 中转；❌ 原生 App；❌ 多用户；❌ 新增监听端口；❌ 任何遥测/外连。

## 3. 架构

```
手机浏览器 / PWA
   │            （链路三选一：LAN ／ Tailscale ／ Cloudflare Tunnel+Access）
   ▼
Hermes dashboard :9119 ── 认证门（密码 ／ M2:配对码）
   ├── Pocket 移动页（插件 UI：会话列表 / 打开对话 / PWA manifest）      ← M2
   └── /api/plugins/pocket/*（插件后端 FastAPI）                        ← M2
            │  仅经回环（localhost）调用；API key 永不出服务端
            ▼
     Hermes API server :8642（会话 / 流式聊天）
   ─────────────────────────────────────────────
     ↑ 与宿主「Hermes 常驻网关」同生命周期（用户已有）
```

### 组件清单
1. **CLI**（M1）：`pocket qr` / `pocket doctor`（M2 加 `pair`）——地址探测（LAN/Tailscale/自定义）、二维码（ASCII+PNG）、前置条件体检。
2. **Dashboard UI 插件**（M2）：移动优先口袋页 + PWA。
3. **Dashboard 后端**（M2）：`/api/plugins/pocket/*` 会话/聊天代理（key 服务端持有）。
4. **配对鉴权**（M2）：自定义 `DashboardAuthProvider`「pocket」，一次性短命码直登（≥128bit、TTL 120s、一次性、不进日志）；【spike 先行，失败则降级为"码=引导+预填"】。

## 4. 安全设计

| 层 | 措施 |
|---|---|
| 网络 | LAN / Tailscale（推荐，零公网）/ CF 隧道；公网场景**必须**加边缘锁（CF Access）。纯密码裸放公网不推荐（官方口径：basic 密码仅受信网络/VPN） |
| 应用 | 复用 dashboard auth gate（scrypt、登录限速 10/min、防枚举、审计日志）；M2 配对码 |
| 凭据 | API key 仅插件后端使用（回环调用）；浏览器侧永不接触 |
| 供应链 | MIT；无遥测/无外连；QR 用 vendored qrcodegen（MIT） |
| 仓库卫生 | 公开仓库不得含本机路径 / 用户名 / 基础设施指纹；本地执行细节放 gitignored 的 `*.local.md`，推送前 grep 自查 |

## 5. 里程碑

- **M0 调研+方案** ✅（本文件 + 调研报告）
- **M1 配对入口 MVP** 🚧（`qr` + `doctor` + 三链路文档；验收=真机扫码→密码→用起来）→ 计划见 `docs/superpowers/plans/`
- **M2 移动口袋页 + 配对码**（dashboard UI/后端、PWA、provider spike）
- **M3 打磨**（轻量流式聊天视图、i18n、`pocket up` 等）
- **M4 开源发布**（README 双语、Release、目录收录 PR 可选）

## 6. 开源计划

- 仓库：`github.com/TerryYu12/hermes-pocket`（公开开发）；MIT © TerryYu12
- 安装：`hermes plugins install TerryYu12/hermes-pocket --enable`
- 目录骨架：`plugin.yaml` / `__init__.py` / `pocket/` / `dashboard/`(M2) / `docs/` / `tests/`

## 7. 已定决策

| # | 决策 | 结果 |
|---|---|---|
| Q1 | 名称 | **hermes-pocket** |
| Q2 | 仓库时机 | **直接公开** |
| Q3 | 许可证 | **MIT** |
| Q4 | M1 范围 | `qr` + `doctor` + 三篇链路文档；`pocket up` 延后至 M3 |
| Q5 | 文档链路侧重 | Tailscale 主推 / LAN 基础 / CF 进阶（含安全前置） |

## 8. 风险与开放问题

| # | 项 | 处置 |
|---|---|---|
| R1 | provider 直登可行性 | M2 先 spike；降级=码引导 |
| R2 | dashboard UI 移动适配工作量 | 先"能看能聊"最小页 |
| R3 | 与官方 pairing 方向重合 | 插件优先、对齐官方语义，官方落地后转补充 |
| R4 | PTY vs 自研聊天 | M1 用既有页面，M3 再评估 |

## 9. 致谢

- 平台：[Hermes Agent](https://github.com/NousResearch/hermes-agent)（MIT）——网页仪表板（9119）、网关与认证体系均为其自带组件，本插件不含自有后端；
- 工具库：Project Nayuki [QR Code generator](https://www.nayuki.io/page/qr-code-generator-library)（MIT，vendored 于 `pocket/vendor/`）；
- 设计参考：[ZCode](https://github.com/zai-org/ZCode)「Web Remote Control」的产品形态与公开实现（仅参考，未使用其代码）。
