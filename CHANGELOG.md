# Changelog

本文件记录 HEIGO 的版本更新历史。

建议遵循以下约定：

- 参考 Keep a Changelog 的组织方式
- 版本号以根目录 `VERSION` 为唯一来源
- 发布时将 `Unreleased` 中的内容整理为正式版本条目

记录规则：

- 每次准备推送 GitHub 前新增一个版本条目
- 优先使用以下分类：`Added`、`Changed`、`Fixed`、`Refactored`、`Docs`、`Removed`
- 如果变更影响架构、导入、部署或开发流程，需同步更新 `docs/PROJECT_MANUAL.md` 或相关专题文档

## [Unreleased]

### Added

- 新增 `bot/` 目录骨架，提供独立的 QQ 群机器人 FastAPI 服务入口、OneBot 事件路由、命令解析、HEIGO API 客户端与调试接口
- 新增 `bot/Dockerfile` 与 `bot/requirements.txt`，支持机器人服务独立镜像化部署
- 新增 `test_bot_command_service.py` 与 `test_bot_callback.py`，覆盖首版命令解析与回调路由基础行为
- 新增 `/internal/share/player/{uid}` 内部分享页，用于机器人截图与后续图片渲染入口
- 新增 `test_internal_share_page.py`，覆盖内部分享页的基础返回行为
- 新增 Playwright 球员图截图链路与 QQ 群图片回复客户端骨架
- 新增 `test_bot_player_image_reply.py`，覆盖球员图命令的图片回复行为
- 新增 OneBot 事件签名校验与球员图文件缓存 / 失败降级逻辑
- 新增 `test_bot_signature_service.py` 与 `test_bot_render_service.py`，覆盖 OneBot 验签与缓存行为
- 新增 `test_bot_health.py` 与 `test_bot_onebot_client.py`，覆盖机器人健康检查和 OneBot 发送降级路径
- 新增 `test_frontend_admin_entry.js`，覆盖 `heigomanage` 入口、维护中心登录页显示和未登录权限流
- 新增 `scripts/run-core-regressions.ps1`，统一运行主应用安全边界、维护中心入口流和搜索一致性的核心回归集合
- 新增 `scripts/pre-release-check.ps1`，串联文档自检与主应用核心回归，作为本地发布前检查入口
- 新增 `/internal/render/player/{uid}.svg` 内部 SVG 渲染接口，供 `qqbot` 生图链路使用
- 新增 `test_internal_render_svg.py`、`test_share_card_presenter.py` 与 `test_bot_svg_renderer.py`，覆盖服务端 presenter、SVG 路由与 bot 生图链路

### Changed

- `README.md` 不再硬编码版本号，改为声明 `VERSION` 是唯一版本来源
- 根目录 `docker-compose.yml` 正式接入 `napcat` 与 `qqbot` 服务，支持与主应用同机编排部署
- `docker-compose.yml` 将 `napcat` 与 `qqbot` 收敛为可选 `qqbot` profile，避免默认主站部署依赖机器人环境
- `docker-compose.yml` 为 `qqbot` 改为通过 NapCat / OneBot 发送文本与图片，并补充 access token / secret 配置项
- `docker-compose.yml` 收紧 `napcat` 宿主机暴露面，仅默认保留本地 WebUI 端口；主站侧 `INTERNAL_SHARE_TOKEN` 改为可选透传，机器人运行时再显式配置
- `DEPLOY.md` 与 `docs/QQ_BOT_INTEGRATION_PLAN.md` 同步补充 `napcat`、`qqbot` 与内部分享页说明
- 球员搜索与属性搜索同时使用基础归一化和宽松归一化，支持常见欧洲语种特殊字母、德语式 `ae/oe/ue` 输入以及希腊字母的拉丁替代搜索
- `qqbot` 球员图链路从 Playwright/Chromium 截图切换为服务端 SVG + `CairoSVG` 转 PNG，`/health` 配置摘要同步改为 `image_renderer=svg`

### Fixed

- `工资` 命令在球员详情缺失时不再因空值抛错，改为返回明确的缺失提示文本
- OneBot 消息文本预处理补充 CQ `at` / `reply` 标记清理，避免命令解析受到协议片段干扰
- 主应用启动时不再硬编码播种固定管理员密码，改为仅在配置 `HEIGO_BOOTSTRAP_ADMINS` 时显式初始化账号
- `/internal/share/player/{uid}` 支持 `X-Internal-Share-Token` 校验，机器人截图链路同步自动携带该 header
- `heigomanage` 入口不再被未登录状态强制重定向回首页，改为显示维护中心入口并进入管理员登录页
- `heigomanage` 入口补齐首页 Hero 搜索链路，避免只显示维护中心 UI 外壳而无法进入管理员登录态
- 前端 Hero 搜索的归一化和精确命中判断已与后端搜索键规则对齐，支持 `guendogan`、`alexandros`、`Joao` 等输入直达详情
- 机器人 `/health` 会在关键依赖离线时返回 503，并附带配置摘要；OneBot 发送或业务处理异常时改为优先 ack 并尝试文本降级
- 核心回归测试补充 SQLite engine 释放逻辑，清理合并运行时的 `ResourceWarning: unclosed database`

### Docs

- 将 `CHANGELOG.md` 升级为更规范的模板结构，增加 `Unreleased` 段和维护约定
- 新增 `docs/QQ_BOT_INTEGRATION_PLAN.md`，整理基于 NapCat / OneBot 的 QQ 群机器人接入方案、目录结构、接口清单、Docker Compose 增补和命令设计
- 在 `docs/PROJECT_MANUAL.md` 中补充 NapCat / OneBot 机器人专题文档入口
- 在 `docs/PROJECT_MANUAL.md` 中补充搜索能力与搜索约定，记录跨语言字符归一化增强的实际行为
- 在 `docs/PROJECT_MANUAL.md` 中补充 `scripts/run-core-regressions.ps1` 的使用说明和覆盖范围
- 在 `README.md`、`DEPLOY.md`、`DEPLOY_FIRST_RUN_CHECKLIST.md` 与 `docs/PROJECT_MANUAL.md` 中补充 `scripts/pre-release-check.ps1` 与部署前 CI 校验说明
- 更新 `bot/README.md`、`DEPLOY.md` 与 `docs/QQ_BOT_INTEGRATION_PLAN.md`，明确 `qqbot` 为可选 profile、球员图当前主链路为 SVG -> PNG、内部渲染接口新增 `/internal/render/player/{uid}.svg`

## [0.1.0] - 2026-03-19

### Added

- 新增 `VERSION` 作为当前版本唯一来源
- 新增 `CHANGELOG.md` 作为统一更新记录
- 新增 `AGENTS.md` 作为项目级 Agent 上手与协作准则

### Changed

- 重构项目文档体系，明确 `README.md`、`docs/PROJECT_MANUAL.md`、专题文档的职责边界
- 将技术分析、历史审计中的有效内容收敛到 `docs/PROJECT_MANUAL.md`

### Removed

- 删除重复的总览型文档：
  - `docs/HEIGO_AUDIT.md`
  - `docs/TECHNICAL_ANALYSIS_AND_OPTIMIZATION.md`

### Docs

- `README.md` 改为项目入口导航页，不再承载冗长技术说明
- `docs/PROJECT_MANUAL.md` 升级为唯一完整技术文档
- 保留 `docs/IMPORT_TEMPLATE_GUIDE.md`、`DEPLOY.md`、`DEPLOY_FIRST_RUN_CHECKLIST.md` 作为专题文档

## 模板

后续发布可参考以下模板追加新版本：

```md
## [Unreleased]

### Added

- 

### Changed

- 

### Fixed

- 

### Refactored

- 

### Docs

- 

### Removed

- 

## [x.y.z] - YYYY-MM-DD

### Added

- 

### Changed

- 

### Fixed

- 

### Refactored

- 

### Docs

- 

### Removed

- 
```
