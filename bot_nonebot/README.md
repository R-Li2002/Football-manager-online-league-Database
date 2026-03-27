# HEIGO NoneBot2 Bot

这是新的 QQ 机器人目录，职责只有三件事：

1. 接收 NapCat 的 OneBot v11 事件
2. 调用 HEIGO 公开读接口做查询与 UID / 球队解析
3. 生成主站 PNG 签名 URL 并通过 OneBot 发图

当前不再做：

- 本地 SVG -> PNG 转换
- 本地图片缓存
- 直接读取主站 SQLite

## 当前命令

- `球员图 <名字或UID> [+1~+5] [v2026-03]`
- `工资图 <名字或UID>`
- `名单图 <球队名> [第2页]`

示例：

- `球员图 梅西`
- `球员图 梅西 +2 v2026-03`
- `工资图 贝林厄姆`
- `名单图 巴萨 第2页`

## 运行方式

```bash
cd /srv/heigo
cp deploy/heigo.nonebot.env.example .env

docker compose -f docker-compose.yml -f docker-compose.bot.yml up -d --build
```

## NapCat 建议接法

推荐使用 NapCat -> NoneBot2 的 OneBot v11 反向 WebSocket。

建议在 NapCat WebUI 中配置：

- 上报协议：OneBot v11
- 连接方式：反向 WebSocket
- 目标地址：`ws://bot-nonebot:8090/onebot/v11/ws`
- Access Token：与 `.env` 中 `ONEBOT_ACCESS_TOKEN` 保持一致

## 关键环境变量

- `HEIGO_BASE_URL`
- `HEIGO_RENDER_BASE_URL`
- `INTERNAL_RENDER_SIGNING_KEY`
- `HEIGO_RENDER_TTL_SECONDS`
- `QQ_BOT_ALLOWED_GROUPS`
- `QQ_BOT_ALLOW_ALL_GROUPS`
- `BOT_USER_COOLDOWN_SECONDS`
- `BOT_GROUP_LIMIT_PER_MINUTE`
