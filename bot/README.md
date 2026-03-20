# HEIGO QQ Bot

这是 HEIGO 的 QQ 群机器人服务。

当前版本提供：

- FastAPI 服务入口
- OneBot HTTP 事件入口
- 群消息事件归一化
- 命令解析与只读查询编排
- HEIGO 内部 API 客户端
- 机器人 Dockerfile 与依赖文件
- Playwright 球员图截图链路
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

1. 调用 HEIGO `/internal/share/player/{uid}`
2. 使用 Playwright 截图
3. 在 `onebot` 模式下通过 NapCat 自动发送到 QQ 群

当前运行时约定：

- `/health` 会返回 `reply_mode`、`heigo_api`、`onebot_api` 和关键配置是否已设置
- 事件处理过程中如果 HEIGO 请求、渲染或发送失败，会尽量 `ack` 当前事件并返回降级文本，而不是直接抛出 500

推荐部署形态：

`NapCat (QQ 登录与 OneBot 协议) -> HEIGO qqbot-service -> HEIGO 主服务`

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

- `INTERNAL_SHARE_TOKEN` 应与主应用保持一致，用于访问 `/internal/share/player/{uid}`
- `ONEBOT_ACCESS_TOKEN` 与 `ONEBOT_SECRET` 不应留空用于生产环境
- NapCat WebUI 建议只绑定到 `127.0.0.1`
