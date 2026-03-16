# HEIGO Football Manager Online League Database

![HEIGO Admin Dashboard](docs/admin-dashboard.png)

HEIGO 是一套面向 Football Manager 联机联赛的单体式数据平台。它同时承担联赛名单管理、球员属性查询、管理员维护、正式导入、操作审计和线上部署。

当前仓库已经从早期单文件原型，演进为一套可本地开发、可正式导入、可 Docker 部署、可通过 GitHub Actions 自动更新的完整系统。

## 快速入口

- 项目总手册：[docs/PROJECT_MANUAL.md](docs/PROJECT_MANUAL.md)
- 导入模板说明：[docs/IMPORT_TEMPLATE_GUIDE.md](docs/IMPORT_TEMPLATE_GUIDE.md)
- 部署手册：[DEPLOY.md](DEPLOY.md)
- 首次上线清单：[DEPLOY_FIRST_RUN_CHECKLIST.md](DEPLOY_FIRST_RUN_CHECKLIST.md)
- 历史审计与改造说明：[docs/HEIGO_AUDIT.md](docs/HEIGO_AUDIT.md)

## 当前产品定位

HEIGO 当前更适合被理解为：

- 一个面向玩家的联赛数据工作台
- 一个面向管理员的维护与导入后台
- 一个基于 SQLite 的单实例联赛运营系统

它不是通用型 SaaS，也不是多租户平台。当前设计重点是可维护性、导入可靠性和联赛内数据查询体验。

## 核心能力

### 玩家侧

- 首页 Hero 搜索，支持姓名或 UID 快速检索
- 联赛概览页，查看规则、统计和数据状态
- 联赛名单页，按球队、姓名、排序浏览联赛内球员
- 球员库页，搜索完整属性库并进入详情页
- 球员详情页，支持：
  - 基础资料
  - 位置熟练度图
  - 能力雷达图
  - 成长预览
  - 分享图导出
  - 双球员对比
  - 送花 / 踩鸡蛋互动

### 管理侧

- 管理员账号登录 / 登出
- 球员转会、海捞、解约、消费、返老
- 批量转会、批量消费、批量解约
- 撤销操作
- 球队信息修改、球员信息修改、UID 修改
- 正式导入联赛数据
- 工资重算
- 球队统计缓存重建
- 运维审计查看与导出
- 最近一次正式导入结果查看

## 技术栈

- 后端：FastAPI
- ORM：SQLAlchemy 2.x
- 迁移：Alembic
- 数据库：SQLite（当前主方案）
- 数据处理：pandas / openpyxl
- 前端：原生 HTML / CSS / JavaScript
- 部署：Docker CE + Docker Compose + Nginx
- 自动部署：GitHub Actions + SSH

## 本地启动

### 1. 安装依赖

```powershell
cd D:\HEIGOOA
python -m pip install -r requirements.txt
```

### 2. 启动服务

推荐使用项目自带脚本：

```powershell
cd D:\HEIGOOA
.\start_local.ps1
```

或直接运行：

```powershell
cd D:\HEIGOOA
python main1.py
```

默认访问地址：

- [http://127.0.0.1:8001](http://127.0.0.1:8001)

### 3. 健康检查

```powershell
curl http://127.0.0.1:8001/health
```

预期返回：

```json
{"status":"ok","database":"ok"}
```

## 目录结构

```text
HEIGOOA/
├─ alembic/                    # 数据库迁移
├─ deploy/                     # Nginx 模板等部署资源
├─ docs/                       # 项目文档与截图
├─ repositories/               # Repository 层
├─ routers/                    # FastAPI 路由层
├─ services/                   # 业务服务层
├─ static/                     # 前端静态资源
│  ├─ app.html
│  ├─ app.css
│  └─ js/
├─ main1.py                    # 应用装配入口
├─ database.py                 # 数据库初始化 / Alembic 启动入口
├─ import_data.py              # 严格导入核心
├─ docker-compose.yml          # Docker 编排
├─ Dockerfile                  # 应用镜像
├─ DEPLOY.md                   # 部署手册
└─ DEPLOY_FIRST_RUN_CHECKLIST.md
```

## 开发建议

开始继续开发前，先看这几份文档：

1. [docs/PROJECT_MANUAL.md](docs/PROJECT_MANUAL.md)
2. [docs/HEIGO_AUDIT.md](docs/HEIGO_AUDIT.md)
3. [DEPLOY.md](DEPLOY.md)

它们分别覆盖：

- 架构和模块分层
- 已做过的关键改造
- 部署和数据更新方式

## 重要约定

- 文档统一使用 UTF-8 保存
- 生产数据库不要提交到 GitHub
- `data/` 和 `imports/` 由服务器本地持久化
- 更新联赛数据优先走“正式导入”流程
- 如果修改导入、迁移、部署链路，必须同步更新文档
