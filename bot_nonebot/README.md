# HEIGO NoneBot2 Bot

这是新的 QQ 机器人目录，职责只有三件事：

1. 接收 NapCat 的 OneBot v11 事件
2. 调用 HEIGO 公开读接口做查询与 UID / 球队解析
3. 生成主站 PNG 签名 URL 并通过 OneBot 发图

命令会先由 Alconna 做结构化识别；只有球员名存在多个候选时，才由 Waiter 开启 30 秒的同用户、同群/私聊选择会话。两者职责不重叠。

当前不再做：

- 本地 SVG -> PNG 转换
- 本地图片缓存
- 直接读取主站 SQLite

## 当前命令

- `球员图 <名字或UID> [+1~+5]`
- `工资 <名字或UID>`
- `工资图 <名字或UID>`
- `名单 <球队名> [第N页]`
- `名单图 <球队名> [第N页]`
- `新闻 / 足球新闻`
- `早报 / 懂球帝早报`

示例：

- `球员图 梅西`
- `球员图 梅西 +2`
- `工资图 贝林厄姆`
- `名单 巴萨`
- `名单 巴萨 第2页`
- `名单图 巴萨`
- `名单图 巴萨 第2页`

球员名匹配到多个候选时，机器人会返回最多 5 个带 UID 的编号项。直接回复序号即可继续原命令，也可回复“取消”。

球队名单支持当前 54 队的常见中文名、简称和昵称，例如 `巴萨`、`曼联`、`曼城`、`莱斯特城`、`沙尔克`、`药厂`、`葡体`、`大巴黎` 等。名单图固定每页 20 人，文字名单页数由 `BOT_ROSTER_PAGE_SIZE` 配置。

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
- `BOT_ROSTER_PAGE_SIZE`
