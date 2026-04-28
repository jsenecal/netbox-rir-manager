# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.2] - 2026-04-28

First release on the canonical toolkit. Behaviour and plugin code unchanged.

### Added

- `CHANGELOG.md` (this file).
- `Makefile` with canonical targets (`setup`, `migrate`, `runserver`, `nbshell`, `test`, `lint`, `format`, `fix`, `rebuild`, `docs-serve`, `docs-build`).
- Documentation site scaffolding under `docs/` (zensical), auto-deployed to GitHub Pages on push to `main`.
- `release-drafter` workflow that drafts release notes from PR titles using conventional-commits prefixes.
- `pr-title` workflow enforcing conventional-commits PR titles.
- `commit-msg` pre-commit stage that rejects AI / Claude attribution lines.
- `.git-template/hooks/commit-msg` (canonical hook tracked in-tree).
- `renovate.json` (Mend Renovate, `config:recommended`).

### Changed

- CI: expanded matrix to Python 3.12-3.14; switched dependency installation to `uv` with caching; activates the workspace `.venv` via `GITHUB_PATH` so plain `python` works after `cd` into NetBox; Codecov upload now uses OIDC (tokenless).
- Pre-commit: added `pre-commit-hooks` (trailing whitespace, EOF, YAML/TOML checks) alongside ruff.
- Ruff: extended lint selectors with `N`, `A`, `C4`, `DJ`, `PIE` and added explicit `format` config.
- README trimmed; full Dev Container guide and detailed dev workflow moved into the docs site.

### Fixed

- `release-drafter.yml` autolabeler syntax (was `title: { prefix: "feat" }`, now a proper regex list per the v6 schema).
- ASCII-only output across the toolkit: dropped emojis from `release-drafter` category titles and unicode punctuation from generated docs.

## [0.3.1] - 2026-04-13

### Added

- Dev Container documentation in README (later moved to docs/).

### Changed

- Devcontainer image upgraded to netbox-docker 4.0.0.

## [0.3.0] - 2026-03-15

### Added

- Initial pluggable backend architecture (ARIN backend) with sync, write operations, and ticket tracking.
- Per-user API keys with at-rest encryption.
- REST API endpoints under `/api/plugins/rir-manager/`.
- Sync logging with full audit trail.
- Auto-link to NetBox IPAM (Aggregates, Prefixes, ASNs) when `auto_link_networks` is enabled.
