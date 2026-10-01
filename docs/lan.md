# 局域网（LAN）接入

> 最短路径：手机与电脑连同一个 Wi-Fi，扫码即用。适合在家、办公室等受信网络。

## 适用场景

- 手机和运行 Hermes 的电脑处在**同一局域网**（同一路由器下的 Wi-Fi 或有线网络）；
- 临时、便捷地把 Hermes 打开到手机上，不想引入任何外部服务；
- 已经把 Hermes 常驻网关跑在局域网内，只需要一个能扫的入口。

> 局域网只是链路之一。出门在外或跨网访问，优先看 [`tailscale.md`](tailscale.md)；需要公网域名再考虑 [`cloudflare.md`](cloudflare.md)。

## 前置条件

1. **API server 已启用**：在 `HERMES_HOME/.env` 中设置
   ```
   API_SERVER_ENABLED=true
   API_SERVER_KEY=<your-api-key>
   ```
   改完重启网关。
2. **dashboard 绑定到 `0.0.0.0` 并配置了认证**：
   ```bash
   hermes dashboard --host 0.0.0.0 --port 9119
   ```
   仅绑定回环（默认）时，手机连不上；因此必须绑定 `0.0.0.0`。**绑定 `0.0.0.0` 后，认证门必须开启**——局域网内任何设备都能访问该端口，别用空密码裸奔。
3. 已安装本插件（`hermes plugins install <repo> --enable`）。
4. 手机与电脑在同一个二层网络，且没有禁用本地互访。

## 步骤

1. 体检，确认前置条件：
   ```bash
   hermes pocket doctor
   ```
   期望：`API server` 与 `Dashboard` 为 ✓，`Tailscale` / `cloudflared` 显示为可选信息（本链路用不上）。

2. 生成配对二维码：
   ```bash
   hermes pocket qr
   ```
   终端会列出探测到的候选地址（局域网 IPv4 会排在前面），并渲染出 ASCII 二维码。

3. 手机连上同一 Wi-Fi → 用相机或扫码 App 扫码 → 浏览器打开地址（形如 `http://192.168.x.x:9119`）→ 输入 dashboard 密码 → 进入会话。

4. 如需保存图片或换候选：
   ```bash
   hermes pocket qr --png ~/hermes-qr.png      # 同时保存 PNG
   hermes pocket qr --select 1                  # 选择第 2 个候选地址
   hermes pocket qr --list                      # 只列出候选地址
   ```

## 验证

- `hermes pocket doctor` 里 `API server`、`Dashboard` 均为 ✓；
- `hermes pocket qr --list` 中能看到形如 `http://192.168.x.x:9119 (lan)` 的候选；
- 手机浏览器打开该地址，出现 dashboard 登录页并能成功登录、发消息；
- 若换了网络或地址变了，重新跑一次 `hermes pocket qr` 即可。

## 排错

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 手机扫出来打不开，转圈超时 | 电脑防火墙拦了 9119 | 放行入站 TCP `9119`（Windows 防火墙 / macOS 防火墙 / Linux `ufw`、`firewalld` 等），或临时在受信网络内允许 |
| 电脑自己能开、手机不行 | AP 隔离 / 客户端隔离（常见于访客 Wi-Fi、路由器"AP 隔离"开关） | 关掉路由器的 AP 隔离；或换到主 Wi-Fi、改走 [`tailscale.md`](tailscale.md) |
| 手机浏览器提示无法访问但地址没错 | 手机开着 VPN，流量被隧道走了 | 临时关闭手机 VPN 后重试（VPN 会改变路由，导致访问不到本地网段） |
| `doctor` 显示 `Dashboard: running without auth` | dashboard 未配置认证 | 配置 dashboard 认证后再绑定 `0.0.0.0`，不要无密码暴露 |
| `doctor` 显示 `API server ... unreachable` | `.env` 未启用 API server | 按提示设置 `API_SERVER_ENABLED=true` 与 `API_SERVER_KEY`，重启网关 |
| 候选里没有局域网地址 | 多网卡 / 虚拟网卡干扰，探测到的不是主网卡 | 用 `hermes pocket qr --url http://192.168.x.x:9119` 直接指定正确地址 |
