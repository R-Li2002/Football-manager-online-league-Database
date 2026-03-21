# HEIGO QQ Bot

这是 HEIGO 的 QQ 群机器人服务。

当前版本提供：

- FastAPI 服务入口
- OneBot HTTP 事件入口
- 群消息事件归一化
- 命令解析与只读查询编排
- HEIGO 内部 API 客户端
- 机器人 Dockerfile 与依赖文件
- 服务端 SVG 拉取 + PNG 转换球员图链路
- NapCat / OneBot 消息发送客户端
- 健康检查与配置摘要接口
- 图片发送失败后的文本降级

当前支持两种回复模式：

- `BOT_REPLY_MODE=echo_response`
  - 仅回显内部处理结果，适合本地调试
- `BOT_REPLY_MODE=onebot`
  - 调用 NapCat 提供的 OneBot HTTP API 发送文本或球员图
- `BOT_REPLY_MODE=off`
  - 只接收事件，不实际回消息

球员图命令会：

1. 调用 HEIGO `/internal/render/player/{uid}.svg`
2. 使用 `CairoSVG` 转成 PNG 并写入本地缓存
3. 在 `onebot` 模式下通过 NapCat 自动发送到 QQ 群
4. 同时保留 `/internal/share/player/{uid}` 作为人工查看与失败降级链接

当前运行时约定：

- `/health` 会返回 `reply_mode`、`heigo_api`、`onebot_api`、`image_rendering` 和关键配置是否已设置
- 事件处理过程中如果 HEIGO 请求、渲染或发送失败，会尽量 `ack` 当前事件并返回降级文本，而不是直接抛出 500

推荐部署形态：

`NapCat (QQ 登录与 OneBot 协议) -> HEIGO qqbot-service -> HEIGO 主服务`

当前部署约定：

- `qqbot` 与 `napcat` 默认通过 Compose `profile` 可选启用
- 主站默认部署不构建 `qqbot`
- 启用机器人时使用 `docker compose --profile qqbot up -d --build`

当前关键环境变量：

- `HEIGO_BASE_URL`
- `BOT_RENDER_BASE_URL`
- `INTERNAL_SHARE_TOKEN`
- `ONEBOT_API_ROOT`
- `ONEBOT_ACCESS_TOKEN`
- `ONEBOT_SECRET`
- `ONEBOT_SELF_ID`
- `QQ_BOT_ALLOWED_GROUPS`
- `QQ_BOT_ALLOW_ALL_GROUPS`

安全建议：

- `INTERNAL_SHARE_TOKEN` 应与主应用保持一致，用于访问 `/internal/share/player/{uid}` 与 `/internal/render/player/{uid}.svg`
- `ONEBOT_ACCESS_TOKEN` 与 `ONEBOT_SECRET` 不应留空用于生产环境
- NapCat WebUI 建议只绑定到 `127.0.0.1`

部署补充约定：
- 建议先复制 `deploy/heigo.qqbot.env.example` 到服务器 `/srv/heigo/.env`
- NapCat 登录态与配置持久化在宿主机 `data/napcat/qq` 和 `data/napcat/config`
- `qqbot` 的 PNG 缓存持久化在宿主机 `data/qqbot-output`
- 建议使用专用闲置 QQ 号登录 NapCat，而不是日常主号
- 如 `6099` 只绑定 `127.0.0.1`，可通过 `ssh -L 6099:127.0.0.1:6099 deploy@your-server-ip` 访问 WebUI
