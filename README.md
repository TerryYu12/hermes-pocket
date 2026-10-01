# hermes-pocket

> **把自托管 Hermes 装进口袋** —— 扫码 / 密码 → 手机打开移动友好的页面 → 从任何网络接着用你自己的 Hermes。
> *Scan, open, chat — bring your self-hosted Hermes Agent to your phone. No cloud relay. No telemetry.*

**状态：开发中（M1 进行时）** ｜ 设计文档：[`docs/design.md`](docs/design.md) ｜ M1 实施计划：[`docs/superpowers/plans/2026-10-01-m1-pairing-entry.md`](docs/superpowers/plans/2026-10-01-m1-pairing-entry.md)

---

## 这是什么

一个 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 插件：

- `hermes pocket qr` —— 生成配对二维码（终端 ASCII + 可选 PNG），手机扫码直达你的 Hermes 网页端；
- `hermes pocket doctor` —— 检查远端访问前置条件（API server / dashboard 认证 / Tailscale / 隧道），给出修复建议。

**核心取舍：不建云端中转。** 复用你已有的常驻 Hermes 网关（dashboard + API server），手机经 LAN / Tailscale / Cloudflare Tunnel(+Access) 三选一链路直达——这也是它和"带云 relay 的远控方案"的根本区别。

## 安全原则

- **零遥测、零外部上报**（这是设计约束，不随版本变化）；
- 复用官方 dashboard 认证门（密码 / 计划中的一次性配对码），公网场景要求边缘锁（如 Cloudflare Access）；
- 不新增监听端口、不改动 Hermes core、API key 永不进入浏览器。

## 快速上手

```bash
# 1. 安装并启用插件
hermes plugins install TerryYu12/hermes-pocket --enable

# 2. 体检：检查 API server / dashboard 认证 / Tailscale / 隧道等前置条件
hermes pocket doctor

# 3. 生成配对二维码：手机扫码直达你的 Hermes
hermes pocket qr
```

开发期（未发布版本）可本地安装：

```bash
hermes plugins install "file://<path-to-repo>" --enable
```

## 文档索引

| 文档 | 内容 |
|---|---|
| [`docs/lan.md`](docs/lan.md) | 局域网接入：同 Wi-Fi 扫码即用，最短路径 |
| [`docs/tailscale.md`](docs/tailscale.md) | Tailscale 接入（推荐）：跨网访问、零公网暴露 |
| [`docs/cloudflare.md`](docs/cloudflare.md) | Cloudflare Tunnel + Access（进阶）：公网域名，**必须先配 Access** |
| [`docs/design.md`](docs/design.md) | 设计文档：目标、架构、安全设计、里程碑 |
| [`docs/superpowers/plans/2026-10-01-m1-pairing-entry.md`](docs/superpowers/plans/2026-10-01-m1-pairing-entry.md) | M1 配对入口实施计划 |

## 路线图

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M1 | 配对入口：`qr` + `doctor` + 三链路文档 | 🚧 |
| M2 | 移动口袋页（PWA）+ 一次性配对码直登 | 计划中 |
| M3 | 轻量流式聊天视图等打磨 | 计划中 |
| M4 | 开源发布 / 插件目录收录 | 计划中 |

## License

MIT © 2026 TerryYu12

## English (short)

A Hermes Agent plugin that brings your self-hosted agent to your phone: pairing QR → mobile-friendly web entry → reachable over LAN / Tailscale / Cloudflare Tunnel. **Zero cloud relay, zero telemetry.** `hermes pocket doctor` checks the remote-access prerequisites. Install (after v0.1.0): `hermes plugins install TerryYu12/hermes-pocket --enable`.
