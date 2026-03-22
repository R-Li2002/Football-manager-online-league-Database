# Changelog

All notable changes to HEIGO are documented here.

## [Unreleased]

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
