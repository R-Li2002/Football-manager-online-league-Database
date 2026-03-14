# HEIGO Docker 部署手册

这份手册按 Ubuntu + Docker CE 的线上部署方式整理，默认目标是：

- 代码来自 GitHub
- 容器负责运行应用
- SQLite 数据库存放在宿主机挂载目录
- 导入用的 Excel / CSV 不进入镜像，只放在宿主机挂载目录

## 1. 部署目录

建议在服务器上使用固定目录，例如：

```bash
/srv/heigo
```

目录结构建议如下：

```text
/srv/heigo
├─ docker-compose.yml
├─ Dockerfile
├─ data/        # 生产数据库和自动备份
└─ imports/     # 联赛 Excel 和球员属性 CSV
```

## 2. 服务器准备

安装基础工具：

```bash
sudo apt update
sudo apt install -y git
docker --version
docker compose version
```

如果 `docker compose` 不可用，先把 Docker Compose 插件装好，再继续。

## 3. 首次部署

### 3.1 拉代码

```bash
sudo mkdir -p /srv
cd /srv
sudo git clone https://github.com/R-Li2002/Football-manager-online-league-Database.git heigo
cd /srv/heigo
```

### 3.2 创建持久化目录

```bash
mkdir -p data data/backups imports
```

### 3.3 准备数据库

二选一：

1. 如果你已经有本地生产库，把它复制到：

```bash
/srv/heigo/data/fm_league.db
```

2. 如果你没有现成数据库，可以先启动空库，再通过后台“正式导入”或命令行导入数据。

## 4. 启动容器

```bash
cd /srv/heigo
docker compose up -d --build
```

检查容器状态：

```bash
docker compose ps
docker compose logs -f heigo
```

健康检查：

```bash
curl http://127.0.0.1:8080/health
```

返回 `{"status":"ok","database":"ok"}` 说明应用和数据库都已连通。

## 5. 当前 Docker 约定

当前部署文件默认使用这些路径：

- 应用端口：`8080`
- SQLite 数据库：`/app/data/fm_league.db`
- 导入目录：`/app/imports`
- 自动备份目录：`/app/data/backups`

这几个路径都已经写进 Dockerfile 和 docker-compose.yml，不需要额外再手动设置。

## 6. 代码更新流程

这套部署默认是“GitHub 管代码，服务器目录管数据”。

更新代码时执行：

```bash
cd /srv/heigo
git pull origin main
docker compose up -d --build
```

这一步只更新代码和镜像，不会覆盖：

- `data/fm_league.db`
- `data/backups/*`
- `imports/*`

前提是你不要把生产数据库提交到 GitHub。

## 7. 导入联赛数据

把导入文件放到：

```text
/srv/heigo/imports
```

系统会从这里读取最新的：

- `*HEIGO*.xlsx`
- `*球员属性*.csv`

然后你可以用两种方式导入：

### 7.1 后台正式导入

1. 打开站点
2. 登录维护中心
3. 执行“正式导入最新联赛数据”

### 7.2 容器内命令行导入

```bash
cd /srv/heigo
docker compose exec heigo python import_data.py --dry-run --report-json /app/data/strict_import_report.json
```

正式写入：

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

## 8. 数据库备份与回滚

正式导入前，系统会自动把 SQLite 备份到：

```text
/srv/heigo/data/backups
```

你也可以手动备份：

```bash
cp /srv/heigo/data/fm_league.db /srv/heigo/data/backups/fm_league_manual_$(date +%Y%m%d_%H%M%S).db
```

回滚方法：

```bash
cp /srv/heigo/data/backups/某个备份文件.db /srv/heigo/data/fm_league.db
docker compose restart heigo
```

## 9. 反向代理

当前 compose 把应用绑定到：

```text
127.0.0.1:8080
```

这意味着：

- 容器不会直接暴露到公网
- 你应该再加一层 Nginx 或 Caddy 做域名和 HTTPS

Nginx 生产配置模板：

```text
deploy/nginx/heigo.example.conf
```

上线时把里面的：

- `example.com`
- `www.example.com`

替换成你的真实域名，然后执行：

```bash
sudo apt update
sudo apt install -y nginx certbot
sudo systemctl stop nginx
sudo certbot certonly --standalone -d example.com -d www.example.com
sudo cp deploy/nginx/heigo.example.conf /etc/nginx/sites-available/heigo.conf
sudo ln -s /etc/nginx/sites-available/heigo.conf /etc/nginx/sites-enabled/heigo.conf
sudo nginx -t
sudo systemctl start nginx
sudo systemctl reload nginx
```

如果你已经配了 HTTPS，保留 `SESSION_COOKIE_SECURE=true`。

## 10. GitHub Actions 自动部署

仓库已经提供自动部署 workflow：

```text
.github/workflows/deploy.yml
```

触发方式：

- push 到 `main`
- GitHub Actions 页面手动点 `Run workflow`

这个 workflow 会在服务器上执行：

```bash
cd /srv/heigo
git fetch origin main
git checkout main
git pull --ff-only origin main
docker compose up -d --build --remove-orphans
```

然后它会用容器内的 `/health` 接口做部署后验证。

你需要在 GitHub 仓库里配置这 3 个 Secrets：

- `DEPLOY_HOST`：云服务器公网 IP 或域名
- `DEPLOY_USER`：服务器登录用户
- `DEPLOY_SSH_KEY`：这个用户对应的私钥

首次上线时，直接按这份清单走：

```text
DEPLOY_FIRST_RUN_CHECKLIST.md
```

默认部署目录写死为：

```text
/srv/heigo
```

如果你服务器不是这个路径，改 `.github/workflows/deploy.yml` 里的 `DEPLOY_PATH`。

## 11. 关键原则

1. GitHub 只存代码，不存生产数据库
2. `data/` 和 `imports/` 由宿主机持久化
3. 更新代码只做 `git pull + docker compose up -d --build`
4. 更新联赛数据走后台正式导入或容器内导入命令
5. 生产故障优先回滚数据库，再排查代码

## 12. 常用命令

查看容器：

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

重新构建并启动：

```bash
docker compose up -d --build
```
