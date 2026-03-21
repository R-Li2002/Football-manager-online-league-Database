# HEIGO 服务器首次上线清单

这份清单只覆盖第一次把 HEIGO 部署到新服务器时必须完成的动作。

## 1. 服务器基础检查

确认服务器已经具备：

- Ubuntu
- Docker CE
- Docker Compose 插件
- git
- 一个普通部署用户，例如 `deploy`

检查命令：

```bash
ssh deploy@your-server-ip
docker --version
docker compose version
git --version
```

如果 `git` 未安装：

```bash
sudo apt update
sudo apt install -y git
```

## 2. 生成 GitHub Actions 用的 SSH Key

在本地电脑执行：

```bash
ssh-keygen -t ed25519 -C "github-actions-heigo" -f ~/.ssh/heigo_github_actions
```

会得到两个文件：

- 私钥：`~/.ssh/heigo_github_actions`
- 公钥：`~/.ssh/heigo_github_actions.pub`

## 3. 把公钥加到服务器

把公钥内容追加到部署用户的 `authorized_keys`：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat >> ~/.ssh/authorized_keys
```

把 `heigo_github_actions.pub` 的整行内容粘进去后，按：

```text
Ctrl + D
```

然后修正权限：

```bash
chmod 600 ~/.ssh/authorized_keys
```

## 4. 验证 SSH Key 可登录

在本地电脑执行：

```bash
ssh -i ~/.ssh/heigo_github_actions deploy@your-server-ip
```

如果能免密登录，再继续后续步骤。

## 5. 准备部署目录

在服务器上执行：

```bash
sudo mkdir -p /srv/heigo
sudo chown -R $USER:$USER /srv/heigo
cd /srv/heigo
git clone https://github.com/R-Li2002/Football-manager-online-league-Database.git .
mkdir -p data data/backups imports data/napcat/qq data/napcat/config data/qqbot-output
```

## 6. 上传数据库

如果你已经有本地数据库，在本地电脑执行：

```bash
scp -i ~/.ssh/heigo_github_actions /path/to/fm_league.db deploy@your-server-ip:/srv/heigo/data/fm_league.db
```

如果暂时没有现成数据库，可以跳过这一步，后面通过正式导入初始化。

## 7. 准备机器人运行参数（如需启用）

如果你准备在这台服务器上同时跑 QQ 机器人，先额外确认：

- 你手上有一枚 **专用闲置 QQ 号**
- 该 QQ 号能正常登录并可加入你的联赛群
- 你有手机可用于 NapCat 首次扫码登录

然后在服务器执行：

```bash
cd /srv/heigo
cp deploy/heigo.qqbot.env.example .env
nano .env
```

首轮建议至少先填：

- `INTERNAL_SHARE_TOKEN`
- `ONEBOT_ACCESS_TOKEN`
- `ONEBOT_SECRET`
- `BOT_REPLY_MODE=onebot`

以下两项可以在 NapCat 首次登录后再补：

- `ONEBOT_SELF_ID`
- `QQ_BOT_ALLOWED_GROUPS`

## 8. 首次手动启动容器

在服务器上执行：

```bash
cd /srv/heigo
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8080/health
```

首次上线建议先只启动主站；`qqbot` 与 `napcat` 可在主站稳定后再通过 `--profile qqbot` 单独启用。

预期返回：

```json
{"status":"ok","database":"ok"}
```

## 9. 配置 GitHub Secrets

打开仓库：

```text
GitHub -> Settings -> Secrets and variables -> Actions
```

新增这三个 Secrets：

### `DEPLOY_HOST`

值：服务器公网 IP 或域名

### `DEPLOY_USER`

值：部署用户，例如：

```text
deploy
```

### `DEPLOY_SSH_KEY`

值：`~/.ssh/heigo_github_actions` 私钥文件的完整内容

注意：

- 必须从 `-----BEGIN OPENSSH PRIVATE KEY-----` 复制到 `-----END OPENSSH PRIVATE KEY-----`
- 不要填 `.pub`

## 10. 首次手动触发 GitHub Actions

进入：

```text
GitHub -> Actions -> Deploy Production -> Run workflow
```

确认 workflow 能完成：

- 发布前检查脚本通过（文档自检 + 主应用核心回归）
- SSH 登录服务器
- `git pull --ff-only origin main`
- `docker compose up -d --build --remove-orphans`
- `/health` 校验通过

## 11. 安装 Nginx

在服务器执行：

```bash
sudo apt update
sudo apt install -y nginx certbot
```

## 12. 申请 HTTPS 证书

先停止可能占用 80 端口的服务：

```bash
sudo systemctl stop nginx
```

申请证书：

```bash
sudo certbot certonly --standalone -d example.com -d www.example.com
```

把 `example.com` 替换成真实域名。

## 13. 启用 Nginx 配置

复制模板：

```bash
cd /srv/heigo
sudo cp deploy/nginx/heigo.example.conf /etc/nginx/sites-available/heigo.conf
sudo nano /etc/nginx/sites-available/heigo.conf
```

编辑后启用：

```bash
sudo ln -s /etc/nginx/sites-available/heigo.conf /etc/nginx/sites-enabled/heigo.conf
sudo nginx -t
sudo systemctl start nginx
sudo systemctl reload nginx
```

## 14. 最终验证

检查：

```bash
curl -I https://example.com
```

至少确认：

- 域名可以打开
- 浏览器证书正常
- 首页正常显示
- 管理员登录正常
- `git push origin main` 后自动部署可用

## 15. 日常更新流程

以后正常更新就是：

1. 本地修改代码
2. `powershell -ExecutionPolicy Bypass -File scripts\pre-release-check.ps1`
3. `git push origin main`
4. GitHub Actions 先运行发布前检查，再自动部署
5. 服务器继续保留原有 `data/` 和 `imports/`

如果后续要启用 QQ 机器人，再额外确认：

- `/srv/heigo/.env` 中已配置 `INTERNAL_SHARE_TOKEN`
- NapCat 已登录并开放 OneBot HTTP API
- NapCat WebUI 仅通过本地 `6099` 或 SSH 隧道访问，不直接对公网开放
- 专用机器人 QQ 号已进入目标联赛群
- 使用 `docker compose --profile qqbot up -d --build` 启动机器人相关服务
