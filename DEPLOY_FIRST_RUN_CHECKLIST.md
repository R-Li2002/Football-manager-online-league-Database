# HEIGO 首次上线检查清单

## 1. 目录与数据

- [ ] `/srv/heigo` 已创建
- [ ] `data/fm_league.db` 已放好，或你确认首次启动后会走正式导入
- [ ] `data/backups/` 已创建
- [ ] `data/share-cache/` 已创建
- [ ] `imports/` 已创建
- [ ] `data/napcat/qq/` 已创建
- [ ] `data/napcat/config/` 已创建

## 2. 环境变量

- [ ] 已从 `deploy/heigo.nonebot.env.example` 复制为 `.env`
- [ ] 已设置 `INTERNAL_SHARE_TOKEN`
- [ ] 已设置 `INTERNAL_RENDER_SIGNING_KEY`
- [ ] 已设置 `ONEBOT_ACCESS_TOKEN`
- [ ] 已设置 `QQ_BOT_ALLOWED_GROUPS` 或 `QQ_BOT_ALLOW_ALL_GROUPS=true`
- [ ] 如需初始化管理员，已临时设置 `HEIGO_BOOTSTRAP_ADMINS`

## 3. 主站启动

- [ ] 已执行 `docker compose up -d --build`
- [ ] `curl http://127.0.0.1:8080/health` 返回正常
- [ ] 主站页面可通过 `http://81.70.199.249` 访问

## 4. 机器人启动

- [ ] 已执行 `docker compose -f docker-compose.yml -f docker-compose.bot.yml up -d --build`
- [ ] `curl http://127.0.0.1:8090/health` 返回正常或可接受的 degraded 信息
- [ ] NapCat WebUI 可登录
- [ ] NapCat 已启用 OneBot v11 反向 WebSocket
- [ ] 反向 WS 地址配置为 `ws://bot-nonebot:8090/onebot/v11/ws`
- [ ] Access Token 与 `.env` 一致

## 5. 业务验证

- [ ] 测试群内 `@机器人 球员图 梅西` 可收到图片
- [ ] 测试群内 `@机器人 工资图 梅西` 可收到图片
- [ ] 测试群内 `@机器人 名单图 Barcelona` 可收到图片
- [ ] 主站 `data/share-cache/` 能看到对应 PNG 缓存

## 6. 上线后收尾

- [ ] 若已完成管理员引导，已删除 `.env` 中的 `HEIGO_BOOTSTRAP_ADMINS`
- [ ] 已确认 `6099` 仅绑定 `127.0.0.1`
- [ ] 已确认不再使用旧 `bot/` 服务做部署入口
- [ ] 已确认当前先按 IP + HTTP 运行，等未来有真实域名后再补 HTTPS
