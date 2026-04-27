# Manual Setup

If you'd rather not use the Dev Container, you can run the plugin against an existing NetBox checkout.

## Clone

```bash
git clone https://github.com/jsenecal/netbox-rir-manager.git
cd netbox-rir-manager
```

## Install dev dependencies

The project uses [`uv`](https://github.com/astral-sh/uv) for environment management:

```bash
uv sync --extra dev
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
```

Or, with plain `pip`:

```bash
pip install -e ".[dev]"
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

## Tests

```bash
make test
```

Tests require a running NetBox environment with PostgreSQL and Valkey (or Redis). The Dev Container provides this out of the box; otherwise, see the [CI workflow](https://github.com/jsenecal/netbox-rir-manager/blob/main/.github/workflows/ci.yml) for an example setup.
