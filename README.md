# HEIGO Football Manager Online League Database

![HEIGO Admin Dashboard](docs/admin-dashboard.png)

HEIGO 是一套面向 Football Manager 联机联赛的单体式数据平台，覆盖联赛名单管理、球员属性查询、管理员维护、正式导入、操作审计与线上部署。

## 当前版本

- 当前版本号以根目录 `VERSION` 文件为唯一来源
- 查看当前版本可直接读取 `VERSION`
  - PowerShell：`Get-Content .\VERSION`
  - Bash：`cat ./VERSION`
- 详细变更历史见 `CHANGELOG.md`

## 快速启动

### 安装依赖

```powershell
cd D:\HEIGOOA
python -m pip install -r requirements.txt
```

### 启动服务

```powershell
cd D:\HEIGOOA
.\start_local.ps1
```

或：

```powershell
cd D:\HEIGOOA
python main1.py
```

默认访问地址：

- [http://127.0.0.1:8001](http://127.0.0.1:8001)

### 健康检查

```powershell
curl http://127.0.0.1:8001/health
```

预期返回：

```json
{"status":"ok","database":"ok"}
```

## 核心文档

- 完整技术文档：`docs/PROJECT_MANUAL.md`
- 更新记录：`CHANGELOG.md`
- Agent 工作准则：`AGENTS.md`
- 导入模板说明：`docs/IMPORT_TEMPLATE_GUIDE.md`
- 部署手册：`DEPLOY.md`
- 首次上线清单：`DEPLOY_FIRST_RUN_CHECKLIST.md`

## 项目定位

- 面向玩家的联赛数据工作台
- 面向管理员的维护与导入后台
- 基于 SQLite 的单实例联赛运营系统

当前重点是可维护性、导入可靠性和联赛内数据查询体验；它不是多租户 SaaS，也不是高并发公网服务。

## 开发与维护约定

- 文档统一使用 UTF-8 保存
- 生产数据库不要提交到 GitHub
- `data/` 和 `imports/` 属于运行时目录
- 更新联赛数据优先走“正式导入”流程
- 每次准备推送前，按需同步更新 `VERSION`、`CHANGELOG.md`、`docs/PROJECT_MANUAL.md` 和相关专题文档
- 推送前可执行 `scripts/release-docs-check.ps1` 做文档同步自检
- 推送前也可执行 `scripts/pre-release-check.ps1`，一次性跑完文档自检和主应用核心回归
