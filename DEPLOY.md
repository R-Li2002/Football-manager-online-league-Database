# HEIGO 联机联赛数据库部署与恢复手册

这份手册按“能直接执行”的原则整理，覆盖本地启动、新机器部署、正式导入、数据库备份恢复、Alembic 升级和紧急修表。

## 1. 环境要求

- Windows PowerShell 或任意可运行 Python 3.12+ 的终端
- Python 依赖已安装：

```powershell
cd D:\HEIGOOA
python -m pip install -r requirements.txt
```

## 2. 本地启动

推荐直接使用内置启动脚本：

```powershell
cd D:\HEIGOOA
.\start_local.ps1
```

或者手动启动：

```powershell
cd D:\HEIGOOA
python main1.py
```

默认访问地址：

- [http://127.0.0.1:8001](http://127.0.0.1:8001)

启动后建议先检查：

```powershell
python audit_schema.py
```

你应该能看到：

- `alembic_version`
- `teams / players / player_attributes / operation_audits`
- 最近一次 `schema_bootstrap` 事件

## 3. 新机器部署

### 3.1 拉取代码并安装依赖

```powershell
git clone <你的仓库地址> D:\HEIGOOA
cd D:\HEIGOOA
python -m pip install -r requirements.txt
```

### 3.2 准备数据库

如果是全新环境，不需要手动建表，应用启动时会自动执行：

- `alembic upgrade head`

如果已有旧库，把数据库文件放到目标位置，然后设置环境变量：

```powershell
$env:DATABASE_PATH = 'D:\HEIGOOA\fm_league.db'
```

也可以直接用默认路径：

- `D:\HEIGOOA\fm_league.db`

### 3.3 启动应用

```powershell
cd D:\HEIGOOA
python main1.py
```

### 3.4 验证部署

```powershell
python test_alembic_migrations.py
python test_phase1.py
python test_simulation.py
python audit_schema.py
```

至少应满足：

- 测试全部通过
- `alembic_version` 为最新 revision
- `operation_audits` 表存在
- 管理员页可以正常登录

## 4. Alembic 升级

正常情况下，应用启动会自动执行：

```powershell
python -m alembic upgrade head
```

如果你要手动升级：

```powershell
cd D:\HEIGOOA
python -m alembic upgrade head
```

查看当前 revision：

```powershell
python -c "import sqlite3; conn=sqlite3.connect(r'D:\HEIGOOA\fm_league.db'); print(conn.execute('select version_num from alembic_version').fetchone()); conn.close()"
```

## 5. 正式导入联赛数据

推荐通过管理员页面执行：

1. 打开管理员页
2. 登录管理员账号
3. 在“系统维护”中点击“执行正式导入”

正式导入会自动做这些事：

- 按严格模式读取 `信息总览 + 联赛名单 + 球员属性.csv`
- 先备份当前 SQLite 数据库
- 正式写入联赛规则、球队、球员和属性库
- 重建球队缓存
- 把导入结果写入 `operation_audits`

如果要在命令行先做检查：

```powershell
python import_data.py --dry-run --report-json strict_import_report.json
```

## 6. 数据库备份

### 6.1 导入前自动备份

管理员页面执行“正式导入”时，会自动生成：

- `fm_league_backup_YYYYMMDD_HHMMSS.db`

### 6.2 手动备份

```powershell
Copy-Item D:\HEIGOOA\fm_league.db D:\HEIGOOA\fm_league_manual_backup_$(Get-Date -Format yyyyMMdd_HHmmss).db
```

## 7. 数据库恢复

恢复前先停服务，然后把备份库覆盖回正式库：

```powershell
Copy-Item D:\HEIGOOA\fm_league_backup_20260311_041118.db D:\HEIGOOA\fm_league.db -Force
```

恢复后执行：

```powershell
python -m alembic upgrade head
python audit_schema.py
python main1.py
```

## 8. 后端审计与日志

当前运维信息分为两层：

- 文件日志：
  - `admin_operations.log`
  - `schema_bootstrap.log`
- 数据库审计：
  - `operation_audits`

现在管理员写操作、正式导入、工资重算、球队缓存重算、schema 启动事件都会进入 `operation_audits`。

历史 `admin_operations.log` 会在应用启动时幂等回填到 `operation_audits`，不会重复导入。

## 9. 紧急修表

正常启动已经不再允许自动 runtime fallback。

如果 Alembic 不可用，而你又必须临时把旧库修到可启动状态，可以手动执行：

```powershell
cd D:\HEIGOOA
python runtime_schema_repair.py
```

执行后请立即检查：

```powershell
python audit_schema.py
```

并确认：

- `schema_bootstrap.log` 里有 `manual_runtime_fallback_started/completed`
- 管理员页的 “Schema 启动状态” 卡片可见这次修表事件

这条路径只适合紧急抢修，不应作为日常升级方式。

## 10. Fly.io 部署要点

如果继续使用 Fly.io：

### 10.1 安装并登录 CLI

```powershell
iwr https://fly.io/install.ps1 -useb | iex
fly auth login
```

### 10.2 创建应用和 Volume

```powershell
cd D:\HEIGOOA
fly apps create heigo-league-db
fly volumes create heigo_data --size 1 --region hkg
```

### 10.3 设置数据库路径

```powershell
fly secrets set DATABASE_PATH=/app/data/fm_league.db
```

### 10.4 部署

```powershell
fly deploy
fly status
fly logs
```

## 11. 常用排查命令

查看最近 schema 启动事件：

```powershell
Get-Content D:\HEIGOOA\schema_bootstrap.log -Tail 20
```

查看最近管理员文件日志：

```powershell
Get-Content D:\HEIGOOA\admin_operations.log -Tail 20
```

查看数据库版本与审计条数：

```powershell
python -c "import sqlite3; conn=sqlite3.connect(r'D:\HEIGOOA\fm_league.db'); cur=conn.cursor(); print('revision=', cur.execute('select version_num from alembic_version').fetchone()[0]); print('operation_audits=', cur.execute('select count(*) from operation_audits').fetchone()[0]); conn.close()"
```

## 12. 推荐操作顺序

日常维护建议始终按下面顺序走：

1. 先备份数据库
2. 再执行正式导入或大范围维护
3. 执行 `python audit_schema.py`
4. 登录管理员页核对审计记录和最新导入摘要
5. 如发现异常，优先回滚数据库备份，再排查问题
