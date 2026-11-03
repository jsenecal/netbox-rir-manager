# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- REST endpoint to trigger an RIR sync, `POST /api/plugins/rir-manager/configs/{id}/sync/`,
  so scripts can bring the plugin back in line with ARIN without a browser session. It
  queues the same job as the config's **Sync** button, run as the requesting user with
  their own key, and answers `202 Accepted` with the core Job to poll at
  `/api/core/jobs/{id}/`; `403` when the user has no key on the config (#54).
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
- The `reassign`, `reallocate` and `delete-arin` API actions answer a result ARIN
  processed immediately, without a ticket, with `200` and
  `{"detail", "recorded", "ticket": null, "net"}` (`net` is the linked child
  network, if any) instead of `201` and a ticket; `recorded` is `false` when ARIN
  made the change but NetBox could not record it. Results with a ticket still
  return `201` and the ticket (#56).

### Fixed

- The daily **Scheduled RIR Sync** now also queues the per-aggregate prefix sync,
  as the manual **Sync** does, so reassignments made outside NetBox are discovered on
  the schedule. Those prefix jobs use the config's default key and run as its owner (#66).
- A config sync fetched and synced a POC once for each role it holds on the org (for
  example a NOC that is also the Tech contact), writing duplicate sync log rows and
  making extra ARIN calls. Each POC is now synced once per run; the org still records
  every role link (#68).
- Reassign and reallocate now reach ARIN (#57). Their network payloads never
  validated against pyregrws (no IP version, and the range was not in a net
  block), so every request failed with a server error before anything was sent.
  The range now goes in a net block typed `S` (reassigned) or `A` (reallocated),
  with the version taken from the start address, and the payload names the parent
  net, which ARIN requires. Verified against ARIN's OT&E environment: simple and
  detailed reassignment, reallocation and removal. For a simple reassignment, the
  customer details are now mapped to the payload ARIN expects (ISO 3166-1 country
  code, numbered street address lines, ISO 3166-2 subdivision code), and accented
  letters in the customer name, street address, city and postal code are
  transliterated to ASCII, since Reg-RWS payloads are ASCII-only. Network or
  customer details that still cannot form a valid payload are reported as a clear
  error, a `400` in the REST API, without contacting ARIN, and the network is
  checked before the customer is created, so a refused network no longer leaves an
  orphan customer at ARIN.
- The daily **Scheduled RIR Sync** never ran: its module was only imported lazily, so the
  `@system_job` registration had not happened when `rqworker` scheduled system jobs at
  startup. The plugin now imports its jobs when it loads (#54).
- The prefix and aggregate syncs skipped every IPv4 /31 and /32 (and IPv6 /127 and
  /128): the ARIN lookup was sent `None` as the end address, so it found nothing
  and the reassignment never got an RIR network, with nothing in the sync logs.
  Every place that computes a prefix's address range now uses one helper that
  returns the real last address for any prefix length (#55).
- Writes ARIN processes immediately, without opening a ticket (NET deletes and
  simple reassignments, for example), no longer fail. The plugin stored a ticket
  with an empty number for the first one, so every later one hit the unique ticket
  number after ARIN had already made the change: the API returned a 500, the UI a
  server error, and NetBox kept no record of a change that had happened (#56).
  Such results are now recorded as a `success` sync log only, and no ticket is
  created; the Reassign, Reallocate and Delete actions return to the network (or
  prefix) page with a message instead of opening a ticket. If NetBox fails to
  record a change ARIN has accepted, the change is no longer reported as failed:
  the error is logged (and written to an `error` sync log when possible) and the
  caller is told the change succeeded at ARIN. Tickets with an empty number left
  by earlier versions are harmless and can be deleted or renamed.
- The Prefix **Reassign** form now submits exactly what it shows, immediately, with
  the user's own key. It used to discard the form, queue the automatic reassign job
  (which derived its own values), and fail unless the parent allocation had
  `auto_reassign` enabled; that flag now only gates the automatic path.
- The Prefix **Reassign** page no longer fails with a server error for prefixes not
  scoped to a site, and the automatic reassign job reports "Prefix has no site"
  instead of crashing. Both read `Prefix.site`, which on current NetBox is a reverse
  relation rather than the prefix's site.
- Reassignments from the Network page and the REST API now link the new child
  network ARIN returns, and the API records the customer it creates for a simple
  reassignment, as the other paths already did. All reassignment paths share one
  implementation.
- Generated net names now follow ARIN's rules (up to 50 ASCII letters, numbers and
  hyphens). The automatic reassignment job and the prefix Reassign form built names
  like `Test Tenant-10.0.1.0/29`, which ARIN rejects; they now produce
  `TEST-TENANT-10-0-1-0-29`, shortening the tenant part when needed and keeping the
  prefix whole. User-supplied names on the Reassign and Reallocate forms and API
  actions are validated against the same rules, with a 50-character limit instead
  of 100.
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
