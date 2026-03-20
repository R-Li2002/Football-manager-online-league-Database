# HEIGO Agent 工作准则

本文件面向进入本仓库工作的 Agent / 自动化编码助手。开始处理任务前，先阅读并遵守以下约定。

## 1. 推荐阅读顺序

1. `README.md`
2. `docs/PROJECT_MANUAL.md`
3. `CHANGELOG.md`
4. `docs/IMPORT_TEMPLATE_GUIDE.md`
5. `DEPLOY.md`

如果任务与部署、首次上线或恢复有关，再继续阅读：

- `DEPLOY_FIRST_RUN_CHECKLIST.md`

## 2. 项目目标与边界

- 这是一个围绕 Football Manager 联机联赛运营的单体式数据平台。
- 当前主形态是单实例部署、SQLite 主库、正式导入驱动数据更新。
- 项目重点是可维护性、导入可靠性、审计可追踪、部署简洁。
- 当前不是多租户 SaaS，也不是高并发公网服务。

## 3. 开发与修改准则

- 先理解现状，再动代码；先读文档与相关模块，不要盲改。
- 尊重现有分层：`routers -> services -> repositories -> database/models`。
- 避免生成冗余代码、重复工具函数、平行实现和无关重构。
- 优先做最小必要改动，修根因，不做“顺手大改”。
- 如果变更影响导入、部署、架构、审计、开发流程，必须同步更新文档。
- 不要新增“第二份总览型技术文档”；总览内容应回写到 `docs/PROJECT_MANUAL.md`。

## 4. 文档维护准则

每次准备推送 GitHub 前，至少检查并按需更新：

1. `VERSION`
2. `CHANGELOG.md`
3. `docs/PROJECT_MANUAL.md`
4. 受影响的专题文档，例如：
   - `docs/IMPORT_TEMPLATE_GUIDE.md`
   - `DEPLOY.md`
   - `DEPLOY_FIRST_RUN_CHECKLIST.md`
5. 如需推送前自检，可运行 `scripts/release-docs-check.ps1`

约定如下：

- `README.md` 只做入口导航，不写详细更新历史。
- `CHANGELOG.md` 是唯一更新记录。
- `docs/PROJECT_MANUAL.md` 是唯一完整技术文档。
- 导入、部署、上线清单等操作型文档独立维护，不并入主手册。

## 5. 任务处理建议

- 先分析文件内容、理解项目架构和业务需求，再确定实现方案。
- 与导入相关任务，优先理解模板、字段映射、严格模式和回滚语义。
- 与后台写操作相关任务，优先确认是否影响审计、统计刷新和事务一致性。
- 与前端相关任务，优先保持模块边界，不回退到“大一统脚本”。
- 与数据库相关任务，优先检查 Alembic、运行时兼容逻辑和 SQLite 边界。

## 6. Skills 使用准则

- 合理使用当前会话已启用的 skills。
- 当任务明显属于文档整理、代码审查、前端实现、测试验证等场景时，优先使用对应 skill 的工作流。
- 使用 skill 是为了提高质量和一致性，不是为了增加不必要的复杂度。

## 7. 交付标准

- 改动应清晰、可解释、可追踪。
- 文档、代码、测试描述应保持一致。
- 任何会影响维护者理解的变化，都应在 `CHANGELOG.md` 中留下记录。
