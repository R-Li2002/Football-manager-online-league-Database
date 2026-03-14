# HEIGO 服务器首次上线清单

这份清单只覆盖第一次把站点上线到新服务器时必须做的动作。

## 1. 服务器基础检查

确认你已经有：

- Ubuntu 服务器
- Docker CE
- Docker Compose 插件
- 一个可登录服务器的普通用户，例如 `deploy`

执行：

```bash
ssh deploy@your-server-ip
docker --version
docker compose version
git --version
```

如果 `git` 还没装：

```bash
sudo apt update
sudo apt install -y git
```

## 2. 生成 GitHub Actions 用的 SSH Key

在你的本地电脑执行：

```bash
ssh-keygen -t ed25519 -C "github-actions-heigo" -f ~/.ssh/heigo_github_actions
```

会得到两份文件：

- 私钥：`~/.ssh/heigo_github_actions`
- 公钥：`~/.ssh/heigo_github_actions.pub`

## 3. 把公钥放到服务器

把公钥内容追加到服务器用户的 `authorized_keys`：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat >> ~/.ssh/authorized_keys
```

把 `heigo_github_actions.pub` 里的整行内容粘进去，回车，再按：

```text
Ctrl + D
```

然后修正权限：

```bash
chmod 600 ~/.ssh/authorized_keys
```

## 4. 验证 SSH Key 可登录

在你的本地电脑执行：

```bash
ssh -i ~/.ssh/heigo_github_actions deploy@your-server-ip
```

能正常登录再继续。

## 5. 在服务器准备部署目录

```bash
sudo mkdir -p /srv/heigo
sudo chown -R $USER:$USER /srv/heigo
cd /srv/heigo
git clone https://github.com/R-Li2002/Football-manager-online-league-Database.git .
mkdir -p data data/backups imports
```

如果你已经有本地数据库，把它传上来：

```bash
scp -i ~/.ssh/heigo_github_actions /path/to/fm_league.db deploy@your-server-ip:/srv/heigo/data/fm_league.db
```

## 6. 首次手动启动容器

```bash
cd /srv/heigo
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8080/health
```

如果返回：

```json
{"status":"ok","database":"ok"}
```

说明容器和数据库都正常。

## 7. 配置 GitHub Secrets

打开仓库：

```text
GitHub -> Settings -> Secrets and variables -> Actions
```

新增这 3 个 Secrets：

1. `DEPLOY_HOST`
- 值：你的服务器公网 IP 或域名

2. `DEPLOY_USER`
- 值：部署用户，例如 `deploy`

3. `DEPLOY_SSH_KEY`
- 值：`~/.ssh/heigo_github_actions` 私钥文件的完整内容

注意：

- 私钥内容要从 `-----BEGIN OPENSSH PRIVATE KEY-----` 到结尾整段复制
- 不要填 `.pub`

## 8. 首次手动触发 GitHub Actions

推送代码后，去：

```text
GitHub -> Actions -> Deploy Production -> Run workflow
```

确认 workflow 能完成以下动作：

- SSH 登录服务器
- `git pull --ff-only origin main`
- `docker compose up -d --build --remove-orphans`
- `/health` 检查通过

## 9. 启用 Nginx

安装：

```bash
sudo apt update
sudo apt install -y nginx certbot
```

## 10. 申请 HTTPS 证书

先停掉可能占用 80 端口的服务：

```bash
sudo systemctl stop nginx
```

申请证书：

```bash
sudo certbot certonly --standalone -d example.com -d www.example.com
```

把 `example.com` 和 `www.example.com` 换成你的真实域名。

## 11. 启用 Nginx 站点配置

复制模板：

```bash
cd /srv/heigo
sudo cp deploy/nginx/heigo.example.conf /etc/nginx/sites-available/heigo.conf
```

编辑配置，把里面的域名替换成真实域名：

```bash
sudo nano /etc/nginx/sites-available/heigo.conf
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/heigo.conf /etc/nginx/sites-enabled/heigo.conf
sudo nginx -t
sudo systemctl start nginx
sudo systemctl reload nginx
```

## 12. 最终验证

检查：

```bash
curl -I https://example.com
```

你至少应该确认：

- 域名能打开
- 浏览器证书正常
- 网站主页正常
- 管理员登录正常
- `GitHub push -> 自动部署` 可用

## 13. 上线后日常更新

以后正常更新流程就是：

1. 本地改代码
2. `git push origin main`
3. GitHub Actions 自动部署
4. 服务器保留原有 `data/` 和 `imports/`
