# HEIGO Football Manager Online League Database

HEIGO 是一个面向 Football Manager 联机联赛运营的单体式数据平台。

当前仓库状态已经收口到这套架构：

- 主站：FastAPI + SQLite
- 分享图：由主站统一渲染 `球员图 / 工资图 / 名单图`
- 机器人：`NapCat + NoneBot2 + OneBot v11`
- 部署：
  - `docker-compose.yml` 只负责主站
  - `docker-compose.bot.yml` 负责 `napcat + bot-nonebot`

## 当前版本

当前版本号以根目录 `VERSION` 为唯一来源。

查看方式：

```powershell
Get-Content .\VERSION
```

## 快速启动

安装主站依赖：

```powershell
cd D:\HEIGOOA
python -m pip install -r requirements.txt
```

本地启动主站：

```powershell
cd D:\HEIGOOA
python main1.py
```

默认访问地址：

- [http://127.0.0.1:8001](http://127.0.0.1:8001)

健康检查：

```powershell
curl http://127.0.0.1:8001/health
```

## 部署入口

- 主部署手册：`DEPLOY.md`
- 首次上线清单：`DEPLOY_FIRST_RUN_CHECKLIST.md`
- 完整技术手册：`docs/PROJECT_MANUAL.md`
- 机器人部署与命令说明：`bot_nonebot/README.md`
- 更新记录：`CHANGELOG.md`
- Agent 约束：`AGENTS.md`

## 当前分享与机器人链路

主站当前内置图片接口：

- `/internal/render/player/{uid}.png`
- `/internal/render/wage/{uid}.png`
- `/internal/render/roster.png?team=...&page=...`

机器人当前只负责：

- 接收群消息
- 调用主站读接口查询球员 / 球队
- 生成主站 PNG 签名 URL
- 通过 OneBot 发图

机器人不再负责：

- 本地 SVG -> PNG 转换
- 本地图片缓存
- 直接读取主站数据库

## 生产部署现状

当前你提供的公网入口是：

- `81.70.199.249`

因此当前推荐做法是：

- 主站通过 Nginx 或直接端口映射对外提供 `http://81.70.199.249`
- `bot-nonebot` 和 NapCat 不对公网开放
- 等未来有真实域名后，再补 HTTPS 证书和 443 配置
