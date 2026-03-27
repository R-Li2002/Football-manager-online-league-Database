# Changelog

All notable changes to HEIGO are documented here.

## [Unreleased]

### Added

- 新增公开页面 `/updates` 与 `/data-feedback`，并从主站页脚提供入口，方便用户查看项目更新历史和提交数据纠错反馈。
- 新增基于 SQLite 的 `data_feedback_reports` 留档能力，并提供后台只读入口查看最近收到的公开纠错反馈。
- 新增 NoneBot `球员图 <名字或UID> +1~+5` 命令形态，可直接请求主站成长预览分享图，默认使用最新属性版本。
- 调整 NoneBot 名单能力与名单分享图为单页最多 20 人，不再暴露翻页用法。

### Refactored

- 将应用启动装配拆分到 `app_bootstrap.py`、`app_security.py` 与 `app_factory.py`，同时保留 `main1.py` 作为脚本与测试的兼容入口。
- 将数据库页的搜索、排行榜与对比夹逻辑拆分为独立前端文件，并由 `static/app.html` 加载。
- 新增 `services/admin_action_runner.py`，统一后台写动作的执行、回滚、transfer log 落库与球队统计刷新边界。
- 重构 `services/transfer_service.py` 与 `services/roster_service.py`，让单球员写动作复用统一 mutation runner，不再重复 commit / log / stat refresh 流程。
- 将 `services/admin_service.py` 与 `services/admin_write_service.py` 收口为兼容聚合层，统一指向新的后台写入口。
- 将正式导入运行时从 `import_data.py` 拆分到 `imports_runtime/`，分别承接报告、来源解析、校验、工作簿解析、属性解析与持久化编排，同时保留 `import_data.py` 兼容 CLI facade。
- 将公开读响应的组装逻辑从 `services/read_service.py` 拆分到 `services/read_presenters.py` 与 `services/team_stat_source_service.py`，使 `read_service.py` 更专注于查询编排。
- 将运维脚本迁移到 `scripts/maintenance/`，并把日志、报表、截图和备份产物归类到 `output/` / `data/backups/`。
- 移除前端详情页、对比页与分享图中的预览 CA 数值推算，成长预览仅保留 `+N` 步进与逆足 `+1` 展示，避免误导用户。

### Tests

- 在 `test_transfer_service.py` 与 `test_roster_service.py` 中新增聚焦单测，覆盖 transfer log 落库、球队统计刷新、球队改名一致性与 UID 引用同步。

### Docs

- 明确联赛导入 `.csv` / `.xlsx` 文件属于数据库导入原始输入，而不是普通代码改动。
- 在 `docs/PROJECT_MANUAL.md` 中补充后台写动作约定，明确哪些层允许 `commit()`，哪些层只应返回 mutation 元数据。
- 在 `docs/PROJECT_MANUAL.md` 中记录 `imports_runtime/` 的拆分与新的导入写边界约定。
- 更新 `README.md` 与 `docs/PROJECT_MANUAL.md`，补充读服务边界调整和根目录清理规则。

## [0.2.1] - 2026-03-25

### Changed

- 完成球员分享卡 v3 布局收口，统一本地化 HTML / SVG 文案、位置图展示和雷达排版。
- 将主站路由和部署环境示例中的默认分享模板版本切换为 `3`。
- 调整 NoneBot 的工资查询逻辑，使 `工资` 返回纯文本计算详情，而 `工资图` 保持为显式图片命令。
- 调整 NoneBot 的名单查询逻辑，使 `名单` 返回纯文本名单详情，而 `名单图` 保持为显式图片命令。
- 扩充 NoneBot 的球队别名覆盖，新增更多中文昵称和英文缩写，并将别名目标对齐到实际数据库球队名，例如 `Man UFC`、`Bayer 04`、`Sporting CP`。
- 在数据库页新增球员互动排行榜，支持鲜花、鸡蛋、净好评，以及球队和版本筛选。

### Docs

- 更新当前服务器入口 `81.70.199.249` 的部署说明，并明确 HTTPS 应等真实域名到位后再接入。

## [0.2.0] - 2026-03-23

### Refactored

- 将分享渲染拆分为独立的 model、HTML、SVG 与 PNG 服务。
- 为主站新增球员图、工资图和名单图的 PNG 渲染能力。
- 将 QQ 机器人实现迁移到基于 NoneBot2 + OneBot v11 的 `bot_nonebot/`。
- 将部署拆分为主站的 `docker-compose.yml` 与 `napcat + bot-nonebot` 的 `docker-compose.bot.yml`。

### Fixed

- 将生产部署和 CI 统一到新的“主站 + 机器人” compose 结构。

### Removed

- 移除旧版 `bot/` 实现及其历史单测。
- 移除旧版 `deploy/heigo.qqbot.env.example` 模板。

### Docs

- 更新部署文档、首次上线清单、README、主手册和 CI 流程，以反映新的“主站出图优先”机器人架构。

## [0.1.0] - 2026-03-19

### Added

- 新增 `VERSION` 作为当前版本号的唯一来源。
- 新增 `CHANGELOG.md` 作为统一更新历史。
- 新增 `AGENTS.md` 作为仓库级 Agent 协作规范。

### Changed

- 将技术总览内容收口到 `docs/PROJECT_MANUAL.md`。
- 明确 README、主手册与操作型文档之间的边界。

### Removed

- 移除重复的总览型文档：
  - `docs/HEIGO_AUDIT.md`
  - `docs/TECHNICAL_ANALYSIS_AND_OPTIMIZATION.md`
