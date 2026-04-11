# HEIGO 部署手册

本文档描述当前推荐的部署结构。

- `docker-compose.yml` 只负责主站 HEIGO
- `docker-compose.bot.yml` 负责 `napcat + bot-nonebot`
- 球员图 / 工资图 / 名单图全部由主站渲染 PNG
- `bot_nonebot/` 只做事件处理、查询编排、签名发图

## 1. 推荐部署结构

```text
GitHub -> 云服务器 /srv/heigo
        -> docker-compose.yml            -> heigo
        -> docker-compose.bot.yml        -> napcat + bot-nonebot
        -> Nginx / HTTP                  -> 主站对外
```

主站与机器人职责边界：

- `heigo`：数据读取、分享 SVG、分享 PNG、PNG 缓存
- `napcat`：QQ 登录态、OneBot 协议桥
- `bot-nonebot`：命令解析、读接口查询、图片 URL 签名、OneBot 发图

## 2. 服务器前置条件

建议环境：

- Ubuntu 22.04 / 24.04
- Docker CE
- Docker Compose 插件
- git
- Nginx（如果要通过 `81.70.199.249` 反代主站）

## 3. 目录结构

```text
/srv/heigo
├─ docker-compose.yml
├─ docker-compose.bot.yml
├─ Dockerfile
├─ bot_nonebot/
├─ data/
│  ├─ fm_league.db
│  ├─ backups/
│  ├─ share-cache/
│  └─ napcat/
└─ imports/
```

说明：

- `data/share-cache/` 由主站持久化 PNG 缓存
- `data/napcat/` 持久化 NapCat 登录态与配置

## 4. 首次准备

```bash
sudo mkdir -p /srv/heigo
sudo chown -R $USER:$USER /srv/heigo
cd /srv/heigo
git clone https://github.com/R-Li2002/Football-manager-online-league-Database.git .
mkdir -p data data/backups data/share-cache imports data/napcat/qq data/napcat/config
```

准备环境变量：

```bash
cp deploy/heigo.nonebot.env.example .env
nano .env
```

至少确认：

- `INTERNAL_SHARE_TOKEN`
- `INTERNAL_RENDER_SIGNING_KEY`
- `ONEBOT_ACCESS_TOKEN`
- `QQ_BOT_ALLOWED_GROUPS` 或 `QQ_BOT_ALLOW_ALL_GROUPS`

## 5. 启动方式

只启动主站：

```bash
docker compose up -d --build
```

主站 + NapCat + NoneBot2：

```bash
docker compose -f docker-compose.yml -f docker-compose.bot.yml up -d --build
```

查看状态：

```bash
docker compose -f docker-compose.yml -f docker-compose.bot.yml ps
docker compose -f docker-compose.yml -f docker-compose.bot.yml logs -f heigo
docker compose -f docker-compose.yml -f docker-compose.bot.yml logs -f bot-nonebot
```

## 6. 健康检查

主站：

```bash
curl http://127.0.0.1:8080/health
```

机器人：

```bash
curl http://127.0.0.1:8090/health
```

## 6.1 公网入口与边界

- 当前公网入口是 `81.70.199.249`
- 目前是 IP，不是真实域名
- Nginx 只需要反代 `127.0.0.1:8080`
- `bot-nonebot` 和 `napcat` 都保持 Docker 内网或宿主机本地访问
- 当前可直接使用 [heigo.example.conf](D:\HEIGOOA\deploy\nginx\heigo.example.conf) 里的 IP 版 HTTP 配置
- 等未来有真实域名后，再补 443 / HTTPS 证书配置

## 7. NapCat 配置建议

推荐使用 OneBot v11 反向 WebSocket：

- 目标地址：`ws://bot-nonebot:8090/onebot/v11/ws`
- Access Token：与 `.env` 中 `ONEBOT_ACCESS_TOKEN` 一致

WebUI 端口默认只绑定本机：

```text
127.0.0.1:6099:6099
```

如果服务器只开放 SSH，可本地转发：

```bash
ssh -L 6099:127.0.0.1:6099 deploy@your-server-ip
```

然后访问：

```text
http://127.0.0.1:6099
```

## 8. 当前主站图片接口

- `/internal/render/player/{uid}.png`
- `/internal/render/wage/{uid}.png`
- `/internal/render/roster.png?team=...&page=...`

说明：

- 三类 PNG 都要求签名参数 `exp + sig`
- `bot-nonebot` 负责签名
- 主站负责缓存和真正渲染

## 9. 当前关键环境变量

主站：

- `INTERNAL_SHARE_TOKEN`
- `INTERNAL_RENDER_SIGNING_KEY`
- `HEIGO_SHARE_TEMPLATE_VERSION`
- `SESSION_COOKIE_SECURE`

机器人：

- `HEIGO_BASE_URL`
- `HEIGO_RENDER_BASE_URL`
- `ONEBOT_ACCESS_TOKEN`
- `QQ_BOT_ALLOWED_GROUPS`
- `QQ_BOT_ALLOW_ALL_GROUPS`
- `BOT_USER_COOLDOWN_SECONDS`
- `BOT_GROUP_LIMIT_PER_MINUTE`

## 10. 发布前检查

```bash
powershell -ExecutionPolicy Bypass -File .\scripts\pre-release-check.ps1
```

该脚本当前会检查：

- 文档同步
- 主站核心回归
- 新分享 PNG 路由测试
- `bot_nonebot` 解析 / 调度测试
- `bot_nonebot` 语法编译

## 11. 常见部署排障

### 11.1 宿主机源码已更新，但线上行为没变

这通常不是 Git 没拉下来，而是“宿主机源码”和“运行容器内代码”还没有同步：

- `git pull` 只会更新 `/srv/heigo` 下的源码
- 正在运行的 `heigo` 容器仍然使用旧镜像里的 `/app/*`
- 因此，正式部署仍应执行：

```bash
cd /srv/heigo
docker compose build heigo
docker compose up -d heigo
```

如需先确认运行容器里的代码是否已经生效，可以进入容器检查对应源码片段。

如果镜像重建暂时因为网络问题无法完成，而线上又必须先恢复，可临时采用应急热修：

- 把修复后的文件 `docker cp` 到运行中的 `heigo:/app/...`
- `docker compose restart heigo`

但这只用于应急恢复；网络稳定后仍应补一次正式 `build + up -d`，避免热修内容在下次重建时丢失。

### 11.2 腾讯云上 `docker compose build heigo` 卡在 `pip install`

在腾讯云等网络环境下，`python:3.11-slim` 镜像构建阶段可能长时间卡在：

```text
RUN pip install --no-cache-dir -r requirements.txt
```

这通常是从 PyPI 拉取 `pandas`、`sqlalchemy` 等 wheel 超时，不一定是 Docker 卡死。

推荐处理方式：

1. 先 `Ctrl+C` 中断本次构建
2. 临时把 `Dockerfile` 中的 `pip install` 切到国内镜像并增加超时 / 重试
3. 再重新执行 `docker compose build heigo`

示例：

```bash
cd /srv/heigo
cp Dockerfile Dockerfile.bak
sed -i 's#RUN pip install --no-cache-dir -r requirements.txt#RUN pip install --default-timeout=300 --retries 10 -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --no-cache-dir -r requirements.txt#' Dockerfile
docker compose build heigo
docker compose up -d heigo
```

如清华源不可用，也可以换成其他国内镜像，例如阿里云。

### 11.3 后端接口正常，但网页仍表现为旧逻辑

当前前端静态资源默认会附带 `VERSION` 查询参数；如果发布后浏览器仍保留旧 JS / CSS，可能出现这类现象：

- 属性库页面仍默认查 `2620`，而接口 `/api/attributes/versions` 实际已经返回 `2630`
- 球队工资帽规则已经支持 `额外0.1M工资帽`，但页面展示仍像旧逻辑

推荐排查顺序：

1. 先直接检查接口：

```bash
curl http://127.0.0.1:8080/api/attributes/versions
```

2. 如果接口返回正常，让浏览器强制刷新
3. 如需正式发布新静态资源版本，再同步更新根目录 `VERSION` 后重启主站

示例：

```bash
cd /srv/heigo
printf '0.2.3\n' > VERSION
docker compose restart heigo
```

