# Dev Container

The repository ships a full [Dev Container](https://containers.dev/) configuration that provides a ready-to-go development environment with NetBox, PostgreSQL 18, and Valkey 9.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- Either:
    - [VS Code](https://code.visualstudio.com/) + the Dev Containers extension, or
    - the [devcontainer CLI](https://github.com/devcontainers/cli)

## Quick start

1. Open the repository in VS Code and select **Reopen in Container** when prompted (or run `Dev Containers: Reopen in Container` from the command palette).
2. The container installs the plugin in editable mode, applies migrations, and starts an RQ worker automatically.
3. Start the development server:

```bash
make runserver
```

NetBox is available at `http://localhost:8009` (default credentials: `admin` / `admin`).

## Common tasks

```bash
make test         # run pytest with coverage
make lint         # ruff check + format-check
make fix          # ruff check --fix + format
make docs-serve   # serve docs locally with zensical
```
