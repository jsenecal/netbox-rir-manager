# Contributing

PRs welcome -- especially for additional RIR backends (RIPE, APNIC, LACNIC, AFRINIC).

## Conventions

- **PR titles** follow [conventional commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `ci:`, `perf:`, `build:`, `revert:`). The `pr-title` workflow enforces this.
- **Release notes** are drafted automatically from PR titles by `release-drafter`. The `CHANGELOG.md` file follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
- **Commit messages** must not contain AI/Claude attribution lines -- a `commit-msg` hook rejects them.

## Architecture

The plugin uses a pluggable backend architecture:

- `netbox_rir_manager/backends/base.py` -- abstract `RIRBackend` class.
- `netbox_rir_manager/backends/arin.py` -- ARIN reference implementation.

Backend classes subclass `RIRBackend` and register themselves with `@register_backend`. The views, REST API and jobs currently construct the ARIN backend directly, so a new backend also needs those call sites to choose it; see [Reference: Backends](../reference/backends.md).

## Releasing

```bash
bumpver update --patch   # or --minor / --major
```

This updates `pyproject.toml`, `netbox_rir_manager/__init__.py`, and the `CHANGELOG.md` "Unreleased" section, commits, tags, and pushes. The `publish.yml` workflow takes it from there once a GitHub Release is published from the tag.
