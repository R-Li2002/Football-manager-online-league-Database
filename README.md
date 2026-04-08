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

## 目录补充约定

- `scripts/maintenance/`：运维/排障/修复类脚本入口。
  - `check_*` / `audit_*` / `debug_*`：只读排查脚本。
  - `fix_*` / `recalculate_*` / `init_*`：会写数据库或生成结果的维护脚本。
  - `runtime_schema_repair.py`：仅限应急修复使用。
- `output/`：运行日志、截图、分析报表和其他可再生输出。
- 联赛导入原件可保留在项目根目录或 `imports/`，但不应和普通功能改动混同。

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

## 导入提示

- 正式导入的详细模板、字段和上传约定见 `docs/IMPORT_TEMPLATE_GUIDE.md`。
- 当根目录存在多个 `*球员属性.csv` / `*球员属性.xlsx` 时，系统会自动选最新文件；如果你要明确导入某个版本，例如 `2640球员属性.xlsx`，推荐显式传 `--attributes-csv`。
- 如果新名单里球队名改了、但你想保留 Excel 中的新队名，应先运行 `scripts/maintenance/rename_teams_from_workbook.py` 把系统中的球队名批量对齐，再做正式导入。
