# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- NetBox 4.7 support: CI now also tests against NetBox 4.7.0, with
  Renovate keeping the matrix pinned to the newest release of that
  minor. The README compatibility matrix gains NetBox 4.7 to the
  0.4.x row.
- Optional per-config **default key** (`RIRConfig.default_key`), the only key used for
  work no user initiated, such as the scheduled sync. A migration sets it on every
  config that has exactly one key, so single-key installs keep syncing; configs with
  several keys need one chosen.

### Changed

- **Breaking:** RIR operations a user initiates, including the automatic
  reassignment and removal an IPAM edit triggers, now run only with that user's own
  key, and the job runs as that user. Previously the automatic paths used the first
  key on the config, whoever owned it. Without a key nothing is sent and a `skipped`
  sync log is written.
- **Breaking:** the scheduled sync now uses only the config's default key, once per
  config. Previously it ran once per key that had ever synced the config.
- CI now tests against the latest NetBox 4.5 and 4.6 releases (4.5.10
  and 4.6.10, previously 4.5.8 and 4.5.10), with Renovate keeping the
  matrix pinned to the newest release of each supported minor. The
  README compatibility matrix gains a 0.4.x / NetBox 4.5-4.6 row.
- Aggregate sync now writes a `skipped` sync log row when ARIN has no Net for an
  aggregate's range, in the scheduled and per-config sync as well as the manual
  Aggregate **Sync** button.

### Fixed

- Aggregate sync no longer links an aggregate to whatever Net ARIN reports as most
  specific for its range. The plugin now walks up the Net's parent chain to the Net
  registered to the config's `org_handle`, and skips (with a `skipped` sync log naming
  the owner) aggregates that belong to another org. Previously a customer reassignment
  could anchor an aggregate in place of your own allocation, third-party space was
  synced as if it were yours, and two configs on the same RIR overwrote each other's
  networks.
- The Aggregate **Sync** button now tries every active config the user holds a key
  for on that RIR, instead of only the first config, and links the aggregate to the
  config whose org owns it.
- The Prefix **Sync** button now uses the config that owns the Net anchoring the
  prefix's aggregate, instead of the first active config on the RIR, and refuses
  prefixes whose aggregate is not linked to an active config.
- Deleting a prefix, or saving it with a status other than Active, no longer removes
  its child reassignment at the RIR unless the parent allocation has `auto_reassign`
  enabled and its config is active -- the same opt-in automatic reassignment already
  required. Previously every synced child network was removed on any such IPAM edit.
  Without the opt-in the network is left in place and a `skipped` sync log is written.
- Automatic reassignment no longer fires for prefixes under an allocation whose RIR
  config is inactive; both automatic reassignment and removal now resolve the
  opted-in parent through one `RIRNetwork.auto_reassign_parent_for()` check.

## [0.4.0] - 2026-06-18

### Changed

- ARIN backend: migrated to pyregrws 1.0.0 (pydantic v2). `_safe_serialize` now
  serializes pyregrws models via `model_dump()` instead of the deprecated v1
  `.dict()`. Dependency pin raised to `pyregrws>=1.0.0b6,<2`.

### Fixed

- ARIN backend: under a warnings-as-errors context, the deprecated `.dict()`
  call raised `PydanticDeprecatedSince20`, which the broad `except` in
  `_safe_serialize` swallowed -- silently collapsing every org/poc/net/customer
  payload to an empty dict. Serializing via `model_dump()` removes the
  deprecated path.

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
