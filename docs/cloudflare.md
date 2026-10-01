# Cloudflare Tunnel + Access 接入（进阶）

> **仅进阶场景。** 需要公网域名访问时才考虑；**上公网前必须先配置 Cloudflare Access**。把 dashboard 裸奔在公网是不可接受的。

## 适用场景

- 需要一个**公网可访问的域名**（例如 `hermes.example.com`），而不是私有网络地址；
- 手机、平板、临时设备都可能访问，不想每台都装 VPN；
- 你能接受在 Cloudflare 侧管理身份策略（Access）。

> 如果你只是"在外面也能用"，请优先选 [`tailscale.md`](tailscale.md)——零公网暴露、配置更少。Cloudflare 方案的攻击面更大，必须叠加边缘访问控制。

## 前置条件

1. **Cloudflare Access 已配置（硬性要求）**：
   - 有一个接入 Cloudflare 的域名；
   - 创建一条 Access 应用，覆盖你的 dashboard 域名，策略只放行你自己的身份（邮箱 / 单点登录 / 一次性 PIN）；
   - 未配置 Access 前，**不要**把隧道指向 dashboard。
2. **认证层明确**（二选一，推荐前者）：
   - **回环绑定 + Cloudflare Access 作为唯一入口锁**（推荐，与步骤 1 对应）：dashboard 绑 `127.0.0.1` 时自身认证门不启用，访问控制全部由 Cloudflare Access 承担——因此 Access 策略必须严格（仅放行你自己的身份）。
   - **双锁模式**：dashboard 绑 `0.0.0.0` 且已开启自身认证（认证门会随非回环绑定自动启用），Access 作为边缘第一层；注意这会让 dashboard 同时暴露在局域网，需用防火墙收窄来源。
   - 官方口径：**dashboard 的 basic 密码只适合受信网络 / VPN 场景**，不能作为公网唯一防线。
3. **已安装 `cloudflared`**，并完成 `cloudflared tunnel login` / 创建隧道。
4. `hermes pocket doctor` 中 `cloudflared` 显示为 ✓。

## 步骤

1. 让 dashboard 只在回环上监听（由 `cloudflared` 在本机侧转发，不直接对外）：
   ```bash
   hermes dashboard --port 9119
   ```

2. 配置隧道，把公网主机名指向本机回环的 dashboard 端口。示例 `config.yml`：
   ```yaml
   tunnel: <tunnel-id>
   credentials-file: <path-to-credentials.json>
   ingress:
     - hostname: hermes.example.com
       service: http://127.0.0.1:9119
     - service: http_status:404
   ```

3. （`config.yml` 里已配好主机名时）运行隧道：
   ```bash
   cloudflared tunnel run <tunnel-name>
   ```
   若只想临时验证连通性，也可用快速隧道：
   ```bash
   cloudflared tunnel --url http://127.0.0.1:9119
   ```
   ⚠️ 快速隧道地址随机、不适合作为长期入口，也**不能替代 Access 策略**——生产使用请用带固定主机名的正式隧道。

4. 在 Cloudflare 侧确认 Access 应用已生效（未登录访问应被拦到登录页）。

5. 在 PC 上生成二维码，指向公网地址：
   ```bash
   hermes pocket qr --url https://hermes.example.com
   ```

6. 手机扫码 → 先过 Cloudflare Access → 再登录 dashboard → 进入会话。

## 验证

- `curl -I https://hermes.example.com` 或浏览器直接访问时，**先出现 Cloudflare Access 登录页**，未通过身份校验看不到 dashboard；
- 通过 Access 后能看到 dashboard 登录页，登录成功、能发消息；
- `hermes pocket qr --url https://hermes.example.com` 生成的二维码指向的是公网域名（`https://`），不是内网 IP；
- `hermes pocket doctor` 中 `cloudflared` 为 ✓。

## 排错与注意事项

| 项 | 说明 |
|---|---|
| dashboard 反向代理配置 | dashboard 位于反代之后时，需正确设置 **trusted_proxies**（把 `127.0.0.1` 等本机代理地址列为可信），否则客户端 IP / 转发头处理异常，登录限速与审计可能失真；同时设置 **public_url** 为公网地址（如 `https://hermes.example.com`），保证重定向、链接与生成内容都指向正确的对外地址，而不是回环或内网地址。 |
| 忘记配 Access | **最危险的情况**：隧道一通，dashboard 就等于挂在公网。请先确认 Access 策略生效，再运行隧道。 |
| basic 密码当唯一防线 | 不建议。官方口径明确 basic 密码仅适用于受信网络 / VPN；公网场景应使用 Cloudflare Access（及可用的强认证方式）。 |
| 二维码指向内网 | 生成时显式带 `--url https://hermes.example.com`，不要用自动探测到的内网候选。 |
| 隧道连不上 | 确认 `cloudflared` 进程在跑、`ingress` 的 `service` 指向 `http://127.0.0.1:9119`、dashboard 确实在 `9119` 监听。 |
| 证书 / 域名问题 | 域名须已托管在 Cloudflare；`https` 由 Cloudflare 边缘提供，源站回环无需自签证书。 |
