# Tailscale 接入（推荐）

> **推荐路径。** 电脑和手机加入同一个 Tailscale 私有网络，无论身处何处都能访问，且**零公网暴露**——没有面向互联网开放任何端口，也不需要域名或证书。

## 适用场景

- 想在外面（4G/5G、别人家的 Wi-Fi）也能随时打开家里的 Hermes；
- 不想把 dashboard 暴露到公网，也不想折腾域名、证书、反向代理；
- PC 与手机都能安装 Tailscale（Windows / macOS / Linux / iOS / Android 均可）。

> 与 [`cloudflare.md`](cloudflare.md) 的区别：Tailscale 是私有网络，等价于"把设备放进同一个虚拟局域网"；Cloudflare Tunnel 是公网发布，必须额外加 Cloudflare Access，属进阶方案。

## 前置条件

1. **PC 和手机都安装 Tailscale，并登录同一个账号**（同一 tailnet）。
   - 电脑：从 Tailscale 官网下载安装并登录；
   - 手机：应用商店安装，登录同一账号；
   - 两者在 Tailscale 后台都应显示为已连接、地址为 `100.x.y.z`。
2. **API server 已启用**（`HERMES_HOME/.env` 中 `API_SERVER_ENABLED=true`、`API_SERVER_KEY=<your-api-key>`）。
3. **dashboard 运行中，且绑定到手机能到达的地址**。手机直连 Tailscale IP 时，dashboard 必须监听非回环地址（回环绑定只接受本机连接）：
   ```bash
   hermes dashboard --host 0.0.0.0 --port 9119
   ```
   绑定 `0.0.0.0` 会自动开启认证门——启动前务必先配置好 dashboard 认证（未配置会 fail-closed 拒绝启动）。
   另一种做法是用 `tailscale serve` 把 dashboard 发布为 tailnet 内的 HTTPS 端点（此时可绑定回环，由 Tailscale 在本机侧转发）；插件默认按"直连 Tailscale IP"方式引导。
4. **dashboard 认证已配置**（即使是私有网络，仍建议保留认证门）。

## 步骤

1. 在 PC 上确认 Tailscale 地址：
   ```bash
   tailscale ip -4
   ```
   输出形如 `100.x.y.z`。

2. 生成配对二维码。插件会自动探测 Tailscale 地址并作为候选列出：
   ```bash
   hermes pocket qr
   ```
   或先确认候选：
   ```bash
   hermes pocket qr --list
   ```
   期望看到形如 `http://100.x.y.z:9119 (tailscale)` 的候选。

3. 如需在手机上直接打开（不走扫码），也可在手机浏览器输入该地址。

4. 扫码打开 → 登录 dashboard → 进入会话。

> 提示：若同时存在局域网与 Tailscale 候选，用 `hermes pocket qr --select <index>` 选择要编码的那个；或 `--url http://100.x.y.z:9119` 直接指定。

## 验证

- `tailscale ip -4` 在 PC 与手机上都能拿到 `100.x.y.z` 地址（同一 tailnet）；
- `hermes pocket qr --list` 中出现 `(tailscale)` 候选；
- **在手机流量（关掉 Wi-Fi）下**扫码打开，依然能登录并对话——这是验证"零公网暴露也能随时访问"的关键一步；
- `hermes pocket doctor` 中 `Tailscale` 显示为 ✓。

## 排错与注意事项

| 项 | 说明 |
|---|---|
| 安卓 VPN 槽位互斥 | Android 系统同一时间只允许一个 VPN 生效。若手机开着其他 VPN（或代理 App），Tailscale 会与其抢占槽位，导致 Tailscale 掉线。需要同时使用时，选择支持"共存"的代理方案，或只保留其一。 |
| PC 上与其他代理共存 | 桌面若运行 Clash 等 TUN 模式代理，可能与 Tailscale 的路由/网卡设置冲突，表现为能 ping 通但页面打不开。观察两者的 TUN/路由规则，必要时把 Tailscale 的 `100.64.0.0/10` 网段加入直连/绕过规则。 |
| headscale 兼容 | 使用自建的 [headscale](https://github.com/juanfont/headscale) 控制面同样可用——只要 PC 与手机接入同一个 headscale 网络、能互相拿到 `100.x.y.z` 地址即可，插件不依赖 Tailscale 官方服务。 |
| 地址能 ping 但打不开 | 检查 dashboard 是否在跑、端口是否 `9119`；确认手机端 Tailscale 已连接（状态非 offline）。 |
| `doctor` 显示 `Tailscale: not installed (optional)` | 表示 PC 上没检测到 `tailscale` 可执行文件；安装并登录后重试。 |
| 想强制指定地址 | `hermes pocket qr --url http://100.x.y.z:9119`。 |
