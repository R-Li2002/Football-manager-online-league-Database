# HEIGO 部署手册

本文档描述 HEIGO 在 Ubuntu + Docker CE 环境下的推荐部署方式。

目标是：

- GitHub 负责保存代码
- 云服务器负责保存运行时数据
- Docker 负责运行应用
- Nginx 负责域名与 HTTPS
- GitHub Actions 负责自动部署

## 1. 推荐部署方式

当前推荐的生产部署结构是：

```text
GitHub -> 云服务器 /srv/heigo -> Docker Compose -> Nginx -> 域名 / HTTPS
```

其中：

- 代码通过 `git pull` 或 GitHub Actions 更新
- 数据库保存在服务器本地挂载目录
- 导入文件保存在服务器本地挂载目录
- 容器镜像不内置生产数据库
- 如启用 QQ 群机器人，可在同一套 `docker-compose.yml` 中通过 `qqbot` profile 额外挂载 `napcat` 与 `qqbot` 服务

## 2. 服务器前置条件

服务器建议满足：

- Ubuntu 22.04 或 24.04
- Docker CE
- Docker Compose 插件
- git
- 一个可用于部署的普通用户，例如 `deploy`

检查命令：

```bash
docker --version
docker compose version
git --version
```

## 3. 部署目录结构

推荐使用固定目录：

```text
/srv/heigo
```

最终目录结构建议如下：

```text
/srv/heigo
├─ docker-compose.yml
├─ Dockerfile
├─ data/
│  ├─ fm_league.db
│  └─ backups/
└─ imports/
```

说明：

- `data/` 保存生产数据库和备份
- `imports/` 保存联赛 Excel 与属性 CSV
- 这两个目录都不应该由 GitHub 管理

## 4. 首次部署

### 4.1 拉取代码

```bash
sudo mkdir -p /srv/heigo
sudo chown -R $USER:$USER /srv/heigo
cd /srv/heigo
git clone https://github.com/R-Li2002/Football-manager-online-league-Database.git .
```

### 4.2 创建运行时目录

```bash
mkdir -p data data/backups imports
```

### 4.3 准备数据库

二选一：

#### 方案 A：上传现成数据库

把本地可用的 `fm_league.db` 复制到：

```text
/srv/heigo/data/fm_league.db
```

#### 方案 B：先启动空库，再导入

如果还没有正式数据库，也可以先直接启动，再通过后台“正式导入”写入初始数据。

## 5. Docker 启动

### 5.1 启动容器

```bash
cd /srv/heigo
docker compose up -d --build
```

如果要同时启用 QQ 机器人：

```bash
cd /srv/heigo
docker compose --profile qqbot up -d --build
```

### 5.2 检查状态

```bash
docker compose ps
docker compose logs -f heigo
```

### 5.3 健康检查

```bash
curl http://127.0.0.1:8080/health
```

预期返回：

```json
{"status":"ok","database":"ok"}
```

## 6. 当前 Docker 约定

当前 `docker-compose.yml` 中的关键环境变量是：

- `PORT=8080`
- `HEIGO_PORT_BIND=127.0.0.1:8080:8080`
- `DATABASE_PATH=/app/data/fm_league.db`
- `HEIGO_IMPORT_ROOT=/app/imports`
- `HEIGO_BACKUP_ROOT=/app/data/backups`
- `SESSION_COOKIE_SECURE=auto`
- `HEIGO_BOOTSTRAP_ADMINS=`（仅首次初始化管理员时临时设置）
- `INTERNAL_SHARE_TOKEN=...`（仅启用内部分享页 / SVG 渲染 / qqbot 时需要）

当前 volume 映射是：

- `./data:/app/data`
- `./imports:/app/imports`

这意味着：

- 生产数据库持久化在宿主机 `data/`
- 导入文件持久化在宿主机 `imports/`
- 更新镜像不会覆盖这两类数据

如果启用了 `qqbot` 服务，约定如下：

- `qqbot` 通过 Docker 内网访问 `http://heigo:8080`
- `qqbot` 通过 Docker 内网访问 `http://napcat:3000`
- `qqbot` 默认仅绑定宿主机 `127.0.0.1:8090`
- `qqbot` 通过 `X-Internal-Share-Token` 访问 `/internal/render/player/{uid}.svg`
- `qqbot` 仍可把 `/internal/share/player/{uid}` 作为调试页或失败降级链接
- `napcat` 默认仅对宿主机暴露本地 WebUI 端口 `6099`，OneBot API 通过 Docker 内网访问
- `qqbot` 不直接挂载生产 SQLite 数据目录
- 如需真实向 QQ 群发文本或图片，需在服务器 `.env` 中设置 `BOT_REPLY_MODE=onebot`
- 需在服务器 `.env` 中配置 `ONEBOT_ACCESS_TOKEN`，并建议同步设置 `ONEBOT_SECRET`
- 需在服务器 `.env` 中配置 `INTERNAL_SHARE_TOKEN`，用于保护内部 HTML 分享页与 SVG 渲染接口
- `ONEBOT_API_ROOT` 默认可使用 `http://napcat:3000`
- 球员图默认走 SVG -> PNG 渲染与文件缓存，可通过 `BOT_RENDER_CACHE_TTL_SECONDS` 调整缓存时长

如果启用了 `napcat` 服务，建议额外约定如下：

- 首次启动后先通过 NapCat WebUI 完成扫码登录
- 在 NapCat 中启用 OneBot 11 HTTP API，并将 access token 配置为与 `.env` 一致
- 在 NapCat 中启用 HTTP 上报，指向 `http://qqbot:8090/onebot/events`
- 如配置了 `ONEBOT_SECRET`，需在 NapCat 上报配置中保持一致
- 不要再把 `3000`、`3001` 直接映射到公网；除本机维护外也不要公开 `6099`

如果需要首次初始化管理员，建议只在首启阶段临时设置：

```text
HEIGO_BOOTSTRAP_ADMINS=HEIGO01=StrongPassword1!;HEIGO02=StrongPassword2!
```

约定如下：

- 该变量只用于“首次创建不存在的管理员”
- 一旦管理员创建成功，建议立即从 `.env` 删除
- 不要再使用仓库中的固定默认口令思路

其中端口映射默认值为：

```text
127.0.0.1:8080:8080
```

如果你当前不是通过 Nginx 反代，而是希望直接对外开放 `8080`，不要修改被 Git 管理的 `docker-compose.yml`，改为在服务器的 `/srv/heigo/.env` 写入：

```text
HEIGO_PORT_BIND=8080:8080
```

当前默认 `SESSION_COOKIE_SECURE=auto`，HTTP 直连 `:8080` 时会自动发送非 `Secure` 管理员会话 cookie；如果你确认只会通过域名 / HTTPS 访问，也可以显式写成：

```text
SESSION_COOKIE_SECURE=true
```

`.env` 默认不纳入 Git 管理，这样后续 `git pull --ff-only` 和 GitHub Actions 自动部署都不会再因为 `docker-compose.yml` 本地脏改动而卡住。

## 7. 更新代码

常规更新流程：

```bash
cd /srv/heigo
git pull origin main
docker compose up -d --build
```

这一步会更新：

- 后端代码
- 前端静态资源
- Docker 镜像

不会覆盖：

- `data/fm_league.db`
- `data/backups/*`
- `imports/*`

前提是不要把这些运行时文件提交到 GitHub。

当前 GitHub Actions 在执行服务器部署前，会先在 CI 中运行以下检查：

- `scripts/release-docs-check.ps1`
- `scripts/run-core-regressions.ps1`

只有文档自检与主应用核心回归都通过，才会继续执行生产部署。

## 8. 导入联赛数据

把新数据放到：

```text
/srv/heigo/imports
```

系统默认会识别：

- `*HEIGO*.xlsx`
- `*球员属性*.csv`

### 8.1 通过后台导入

1. 打开站点
2. 登录维护中心
3. 点击“正式导入最新联赛数据”
4. 查看导入结果和运维审计

### 8.2 通过容器内命令导入

先 dry-run：

```bash
cd /srv/heigo
docker compose exec heigo python import_data.py --dry-run --report-json /app/data/strict_import_report.json
```

正式导入：

```bash
cd /srv/heigo
docker compose exec heigo python import_data.py
```

如果要显式指定文件：

```bash
cd /srv/heigo
docker compose exec heigo python import_data.py \
  --workbook /app/imports/你的联赛文件.xlsx \
  --attributes-csv /app/imports/你的球员属性.csv
```

## 9. 备份与回滚

### 9.1 自动备份

正式导入前，系统会自动备份 SQLite 到：

```text
/srv/heigo/data/backups
```

### 9.2 手动备份

```bash
cp /srv/heigo/data/fm_league.db /srv/heigo/data/backups/fm_league_manual_$(date +%Y%m%d_%H%M%S).db
```

### 9.3 回滚

```bash
cp /srv/heigo/data/backups/某个备份文件.db /srv/heigo/data/fm_league.db
docker compose restart heigo
```

## 10. Nginx 与 HTTPS

当前 Compose 默认把应用绑定到：

```text
127.0.0.1:8080
```

推荐做法：

- Docker 仅监听本机回环地址
- Nginx 对外提供 80/443
- 域名经 Nginx 反代到 `127.0.0.1:8080`

如果只是临时直连 IP:8080，也可以在 `.env` 中设置：

```text
HEIGO_PORT_BIND=8080:8080
```

如需强制覆盖管理员会话 cookie 策略，可额外设置：

```text
SESSION_COOKIE_SECURE=auto
```

其中：

- `auto`：HTTP 直连时自动关闭 `Secure`，HTTPS / 反代带 `X-Forwarded-Proto: https` 时自动启用
- `true`：只适合始终通过 HTTPS 访问维护中心
- `false`：仅建议临时内网 / 调试环境使用

Nginx 模板文件：

- `deploy/nginx/heigo.example.conf`

### 10.1 安装 Nginx 与 Certbot

```bash
sudo apt update
sudo apt install -y nginx certbot
```

### 10.2 配证书

如果要为 `fm.example.com` 签证书：

```bash
sudo systemctl stop nginx
sudo certbot certonly --standalone -d fm.example.com
```

### 10.3 启用 Nginx 配置

```bash
cd /srv/heigo
sudo cp deploy/nginx/heigo.example.conf /etc/nginx/sites-available/heigo.conf
sudo nano /etc/nginx/sites-available/heigo.conf
```

将其中域名替换成你的真实域名后，执行：

```bash
sudo ln -s /etc/nginx/sites-available/heigo.conf /etc/nginx/sites-enabled/heigo.conf
sudo nginx -t
sudo systemctl start nginx
sudo systemctl reload nginx
```

## 11. GitHub Actions 自动部署

自动部署 workflow 位于：

```text
.github/workflows/deploy.yml
```

触发方式：

- push 到 `main`
- 在 GitHub Actions 页面手动点击 `Run workflow`

### 11.1 服务器上执行内容

Workflow 会在服务器上执行：

```bash
cd /srv/heigo
git fetch origin main
git checkout main
git pull --ff-only origin main
docker compose up -d --build --remove-orphans
```

之后还会对容器内 `/health` 做部署后校验。

### 11.2 必要 Secrets

在 GitHub 仓库中配置：

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`

默认部署路径是：

```text
/srv/heigo
```

如果服务器实际路径不同，请同步修改 `.github/workflows/deploy.yml` 中的 `DEPLOY_PATH`。

## 12. 常用命令

查看容器状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f heigo
```

重启服务：

```bash
docker compose restart heigo
```

停止服务：

```bash
docker compose down
```

检查健康：

```bash
curl http://127.0.0.1:8080/health
```

## 13. 关键原则

1. GitHub 只管理代码，不管理生产数据库
2. `data/` 和 `imports/` 是运行时目录，必须持久化
3. 更新联赛数据优先走正式导入，而不是直接改库
4. 线上故障优先看容器日志、健康检查和审计记录
5. 紧急修库优先回滚数据库，`runtime_schema_repair.py` 仅作最后手段
