# Changelog

All notable changes to HEIGO are documented here.

## [Unreleased]

### Refactored

- Split app startup wiring into `app_bootstrap.py`, `app_security.py`, and `app_factory.py`, while keeping `main1.py` as the compatibility entrypoint for scripts and tests.
- Extracted database search/leaderboard and compare-dock logic into separate frontend files loaded from `static/app.html`.
- Added `services/admin_action_runner.py` to centralize admin write execution, rollback, transfer-log persistence, and team-stat refresh boundaries.
- Refactored `services/transfer_service.py` and `services/roster_service.py` so single-player write actions reuse the same mutation runner instead of duplicating commit/log/stat-refresh flow.
- Turned `services/admin_service.py` and `services/admin_write_service.py` into compatibility-oriented aggregation layers that point back to the unified admin write entry path.
- Split the formal import runtime out of `import_data.py` into `imports_runtime/` modules for reporting, source resolution, validation, workbook parsing, attribute parsing, and persistence orchestration, while keeping `import_data.py` as the compatibility CLI facade.
- Split public read response assembly out of `services/read_service.py` into `services/read_presenters.py` and `services/team_stat_source_service.py`, so `read_service.py` now focuses on query orchestration.
- Moved operator scripts into `scripts/maintenance/` and grouped generated logs, reports, screenshots, and backup artifacts under `output/` / `data/backups/`.

### Tests

- Added focused unit tests in `test_transfer_service.py` and `test_roster_service.py` for transfer-log persistence, team-stat refresh, team rename consistency, and UID reference sync.

### Docs

- Clarified that league-import `.csv` / `.xlsx` files are treated as raw source inputs for database import rather than normal code changes.
- Documented the new admin write-action contract in `docs/PROJECT_MANUAL.md`, including which layers may `commit()` and which should only return mutation metadata.
- Documented the `imports_runtime/` split and the updated import write-boundary contract in `docs/PROJECT_MANUAL.md`.
- Updated README and `docs/PROJECT_MANUAL.md` with the new read-service boundary notes and root-directory cleanup rules.

## [0.2.1] - 2026-03-25

### Changed

- Finalized the player share card v3 layout with localized HTML/SVG copy, position-map presentation, and aligned radar placement.
- Switched the default share template version to `3` in the main-site router and deployment env example.
- Changed the NoneBot wage query so `工资` returns text-only calculation details, while `工资图` remains the explicit image command.
- Changed the NoneBot roster query so `名单` returns text-only roster details, while `名单图` remains the explicit image command.
- Expanded NoneBot team alias coverage with more Chinese nicknames and English abbreviations, and aligned alias targets to the actual database team names such as `Man UFC`, `Bayer 04`, and `Sporting CP`.
- Added a player reaction leaderboard under the database tab with flowers, eggs, and net-score rankings plus team and version filters.

### Docs

- Updated deployment notes for the current server entry point `81.70.199.249` and clarified that HTTPS should wait until a real domain is available.

## [0.2.0] - 2026-03-23

### Refactored

- Split share rendering into dedicated model, HTML, SVG, and PNG services.
- Added main-site PNG rendering for player, wage, and roster share cards.
- Migrated the QQ bot implementation to `bot_nonebot/` based on NoneBot2 + OneBot v11.
- Split deployment into `docker-compose.yml` for the main app and `docker-compose.bot.yml` for `napcat + bot-nonebot`.

### Fixed

- Normalized production deployment and CI to the new main-app-plus-bot compose layout.

### Removed

- Removed the legacy `bot/` implementation and its old unit tests.
- Removed the old `deploy/heigo.qqbot.env.example` template.

### Docs

- Updated deployment, first-run checklist, README, manual, and CI flow to reflect the new image-first bot architecture.

## [0.1.0] - 2026-03-19

### Added

- Added `VERSION` as the single source of truth for the current release.
- Added `CHANGELOG.md` as the unified release history.
- Added `AGENTS.md` as the repository-level agent collaboration guide.

### Changed

- Consolidated technical overview content into `docs/PROJECT_MANUAL.md`.
- Clarified the boundaries between README, manual, and operational docs.

### Removed

- Removed duplicated overview-style docs:
  - `docs/HEIGO_AUDIT.md`
  - `docs/TECHNICAL_ANALYSIS_AND_OPTIMIZATION.md`
