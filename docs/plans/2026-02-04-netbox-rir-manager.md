# NetBox RIR Manager Plugin Implementation Plan

**Status: COMPLETED** (2026-02-04)

**Goal:** Build a NetBox plugin that integrates with Regional Internet Registry APIs (starting with ARIN via pyregrws) to synchronize and manage IP resources (POCs, Organizations, Networks) directly from within NetBox.

**Architecture:** Pluggable backend system with an abstract `RIRBackend` base class and an initial ARIN implementation using `pyregrws`. Django models store synced RIR data and link to NetBox's existing IPAM objects (RIR, Aggregate, Prefix, ASN). Background jobs handle sync operations. Standard NetBox plugin patterns (views, tables, forms, filtersets, REST API, navigation) provide the UI/API layer.

**Tech Stack:** Python 3.12+, Django 5.x (via NetBox 4.5), NetBox plugin framework, pyregrws (ARIN client), setuptools, ruff, pytest, uv

**Result:** All 21 tasks completed. The phase 2 plan (`2026-02-05-sync-autolink-redesign.md`) was subsequently executed to restructure the data model (RIRAccount → RIRConfig), add per-user API keys, complete sync operations, add auto-linking, and integrate with JobRunner.

---

## Task 1: Project Scaffolding - Git Init and pyproject.toml -- COMPLETED

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `.pre-commit-config.yaml`

**Step 1: Initialize git repo**

```bash
cd /home/jsenecal/Code/netbox-rir-manager
git init
```

**Step 2: Create .gitignore**

Create `.gitignore` with standard Python/Django ignores (matching netbox-notices pattern):

```gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
*.zip

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# pyenv
.python-version

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/

# MacOS FS
.DS_Store

# Git worktrees
.worktrees/

# Claude Code
CLAUDE.md

# uv
uv.lock
```

**Step 3: Create LICENSE**

Apache-2.0 license file with `Copyright 2026 Jonathan Senecal`.

**Step 4: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["netbox_rir_manager", "netbox_rir_manager.*"]

[tool.setuptools.package-data]
netbox_rir_manager = ["templates/**/*"]

[project]
name = "netbox-rir-manager"
version = "0.1.0"
description = "NetBox plugin for managing RIR (ARIN, RIPE, etc.) resources"
readme = "README.md"
license = {text = "Apache-2.0"}
authors = [
    {name = "Jonathan Senecal", email = "jonathan@jonathansenecal.com"},
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Framework :: Django",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]
requires-python = ">=3.12"
dependencies = [
    "pyregrws>=0.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-django>=4.5",
    "pytest-cov>=4.0",
    "ruff>=0.8",
    "pre-commit>=4.0",
]

[project.urls]
Homepage = "https://github.com/jsenecal/netbox-rir-manager"
Source = "https://github.com/jsenecal/netbox-rir-manager"
Tracker = "https://github.com/jsenecal/netbox-rir-manager/issues"

[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["E", "W", "F", "I", "C90", "UP", "B", "SIM"]
ignore = ["E203", "E266"]

[tool.ruff.lint.mccabe]
max-complexity = 18

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401", "F403"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov=netbox_rir_manager --cov-report=term-missing --reuse-db"

[tool.bumpver]
current_version = "0.1.0"
version_pattern = "MAJOR.MINOR.PATCH"
commit_message = "chore: bump version {old_version} -> {new_version}"
tag_pattern = "v{version}"
commit = true
tag = true
push = true

[tool.bumpver.file_patterns]
"pyproject.toml" = [
    'current_version = "{version}"',
    'version = "{version}"',
]
"netbox_rir_manager/__init__.py" = [
    '__version__ = "{version}"',
]
```

**Step 5: Create .pre-commit-config.yaml**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

**Step 6: Commit**

```bash
git add .gitignore LICENSE pyproject.toml .pre-commit-config.yaml
git commit -m "chore: initial project scaffolding"
```

---

## Task 2: Plugin Config and Package Init -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/__init__.py`
- Create: `netbox_rir_manager/constants.py`

**Step 1: Create plugin config**

Create `netbox_rir_manager/__init__.py`:

```python
from netbox.plugins import PluginConfig

__version__ = "0.1.0"


class NetBoxRIRManagerConfig(PluginConfig):
    name = "netbox_rir_manager"
    verbose_name = "NetBox RIR Manager"
    description = "Manage RIR (ARIN, RIPE, etc.) resources directly from NetBox"
    version = __version__
    author = "Jonathan Senecal"
    author_email = "jonathan@jonathansenecal.com"
    base_url = "rir-manager"
    min_version = "4.5.0"
    required_settings = []
    default_settings = {
        "top_level_menu": True,
        "sync_interval_hours": 24,
        "auto_link_networks": True,
        "enabled_backends": ["ARIN"],
    }


config = NetBoxRIRManagerConfig
```

**Step 2: Create constants.py**

Create `netbox_rir_manager/constants.py`:

```python
# RIR backend choices for model fields
RIR_BACKEND_CHOICES = [
    ("ARIN", "ARIN"),
    ("RIPE", "RIPE NCC"),
    ("APNIC", "APNIC"),
    ("LACNIC", "LACNIC"),
    ("AFRINIC", "AFRINIC"),
]
```

**Step 3: Commit**

```bash
git add netbox_rir_manager/__init__.py netbox_rir_manager/constants.py
git commit -m "feat: add plugin config and constants"
```

---

## Task 3: Backend Interface (Abstract Base Class) -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/backends/__init__.py`
- Create: `netbox_rir_manager/backends/base.py`
- Create: `tests/__init__.py`
- Create: `tests/test_backends/__init__.py`
- Create: `tests/test_backends/test_base.py`

**Step 1: Write the failing test**

Create `tests/test_backends/test_base.py`:

```python
from netbox_rir_manager.backends.base import RIRBackend


def test_backend_cannot_be_instantiated():
    """RIRBackend is abstract and should not be instantiated directly."""
    import pytest

    with pytest.raises(TypeError):
        RIRBackend()


def test_backend_requires_name():
    """Subclasses must define name."""

    class IncompleteBackend(RIRBackend):
        name = "TEST"

        def authenticate(self, account):
            return True

        def get_organization(self, handle):
            return {}

        def get_network(self, handle):
            return {}

        def get_poc(self, handle):
            return {}

        def get_asn(self, asn):
            return {}

        def sync_resources(self, account, resource_type=None):
            return []

    backend = IncompleteBackend()
    assert backend.name == "TEST"
    assert backend.authenticate(None) is True
```

**Step 2: Run test to verify it fails**

```bash
cd /home/jsenecal/Code/netbox-rir-manager
pytest tests/test_backends/test_base.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'netbox_rir_manager.backends'`

**Step 3: Write backend base class**

Create `netbox_rir_manager/backends/base.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from netbox_rir_manager.models import RIRAccount


class RIRBackend(ABC):
    """Abstract base class for RIR API backends."""

    name: str

    @abstractmethod
    def authenticate(self, account: RIRAccount) -> bool:
        """Validate credentials and establish connection."""
        ...

    @abstractmethod
    def get_organization(self, handle: str) -> dict[str, Any]:
        """Retrieve organization details by handle."""
        ...

    @abstractmethod
    def get_network(self, handle: str) -> dict[str, Any]:
        """Retrieve network/prefix details."""
        ...

    @abstractmethod
    def get_poc(self, handle: str) -> dict[str, Any]:
        """Retrieve Point of Contact details."""
        ...

    @abstractmethod
    def get_asn(self, asn: int) -> dict[str, Any]:
        """Retrieve ASN details."""
        ...

    @abstractmethod
    def sync_resources(self, account: RIRAccount, resource_type: str | None = None) -> list[dict[str, Any]]:
        """Sync resources from RIR. Returns list of synced resource dicts."""
        ...
```

Create `netbox_rir_manager/backends/__init__.py`:

```python
from netbox_rir_manager.backends.base import RIRBackend

BACKENDS: dict[str, type[RIRBackend]] = {}


def get_backend(rir_name: str) -> type[RIRBackend]:
    """Get a backend class by RIR name."""
    try:
        return BACKENDS[rir_name]
    except KeyError:
        raise ValueError(f"Unknown RIR backend: {rir_name}. Available: {list(BACKENDS.keys())}")


def register_backend(backend_class: type[RIRBackend]) -> type[RIRBackend]:
    """Register a backend class."""
    BACKENDS[backend_class.name] = backend_class
    return backend_class
```

Create empty `tests/__init__.py` and `tests/test_backends/__init__.py`.

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_backends/test_base.py -v
```

Expected: PASS (note: these tests don't require Django since they test pure Python)

**Step 5: Commit**

```bash
git add netbox_rir_manager/backends/ tests/
git commit -m "feat: add abstract RIR backend interface"
```

---

## Task 4: ARIN Backend Implementation -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/backends/arin.py`
- Create: `tests/test_backends/test_arin.py`

**Step 1: Write the failing test**

Create `tests/test_backends/test_arin.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from netbox_rir_manager.backends.arin import ARINBackend
from netbox_rir_manager.backends.base import RIRBackend


def test_arin_backend_is_rir_backend():
    assert issubclass(ARINBackend, RIRBackend)


def test_arin_backend_name():
    assert ARINBackend.name == "ARIN"


def test_arin_backend_init():
    """ARINBackend should accept api_key and optional base_url."""
    backend = ARINBackend(api_key="test-key")
    assert backend.api is not None


def test_arin_backend_init_custom_url():
    backend = ARINBackend(api_key="test-key", base_url="https://reg.ote.arin.net/")
    assert backend.api is not None


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_poc(mock_api_class):
    mock_api = MagicMock()
    mock_poc = MagicMock()
    mock_poc.handle = "JD123-ARIN"
    mock_poc.last_name = "Doe"
    mock_poc.first_name = "John"
    mock_poc.contact_type = "PERSON"
    mock_poc.company_name = "Example Corp"
    mock_poc.city = "Anytown"
    mock_api.poc.from_handle.return_value = mock_poc
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_poc("JD123-ARIN")

    mock_api.poc.from_handle.assert_called_once_with("JD123-ARIN")
    assert result is not None


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_organization(mock_api_class):
    mock_api = MagicMock()
    mock_org = MagicMock()
    mock_org.handle = "EXAMPLE-ARIN"
    mock_org.org_name = "Example Corp"
    mock_api.org.from_handle.return_value = mock_org
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_organization("EXAMPLE-ARIN")

    mock_api.org.from_handle.assert_called_once_with("EXAMPLE-ARIN")
    assert result is not None


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_network(mock_api_class):
    mock_api = MagicMock()
    mock_net = MagicMock()
    mock_net.handle = "NET-192-0-2-0-1"
    mock_net.net_name = "EXAMPLE-NET"
    mock_api.net.from_handle.return_value = mock_net
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_network("NET-192-0-2-0-1")

    mock_api.net.from_handle.assert_called_once_with("NET-192-0-2-0-1")
    assert result is not None


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_poc_error_returns_none(mock_api_class):
    """When pyregrws returns an Error object, get_poc should return None."""
    from regrws.models import Error

    mock_api = MagicMock()
    error = MagicMock(spec=Error)
    error.message = "Not found"
    error.code = "E_OBJECT_NOT_FOUND"
    mock_api.poc.from_handle.return_value = error
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_poc("NONEXISTENT-ARIN")

    assert result is None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_backends/test_arin.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'netbox_rir_manager.backends.arin'`

**Step 3: Write ARIN backend implementation**

Create `netbox_rir_manager/backends/arin.py`:

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from regrws.api.core import Api
from regrws.models import Error

from netbox_rir_manager.backends import register_backend
from netbox_rir_manager.backends.base import RIRBackend

if TYPE_CHECKING:
    from netbox_rir_manager.models import RIRAccount


@register_backend
class ARINBackend(RIRBackend):
    """ARIN Reg-RWS backend using pyregrws."""

    name = "ARIN"

    def __init__(self, api_key: str, base_url: str | None = None):
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.api = Api(**kwargs)

    @classmethod
    def from_account(cls, account: RIRAccount) -> ARINBackend:
        """Create backend instance from an RIRAccount model."""
        return cls(
            api_key=account.api_key,
            base_url=account.api_url or None,
        )

    def authenticate(self, account: RIRAccount) -> bool:
        """Test authentication by attempting to retrieve the org handle."""
        if not account.org_handle:
            return False
        result = self.api.org.from_handle(account.org_handle)
        return not isinstance(result, Error)

    def get_organization(self, handle: str) -> dict[str, Any] | None:
        result = self.api.org.from_handle(handle)
        if isinstance(result, Error):
            return None
        return self._org_to_dict(result)

    def get_network(self, handle: str) -> dict[str, Any] | None:
        result = self.api.net.from_handle(handle)
        if isinstance(result, Error):
            return None
        return self._net_to_dict(result)

    def get_poc(self, handle: str) -> dict[str, Any] | None:
        result = self.api.poc.from_handle(handle)
        if isinstance(result, Error):
            return None
        return self._poc_to_dict(result)

    def get_asn(self, asn: int) -> dict[str, Any] | None:
        # ARIN ASN lookup is done via Whois/RDAP, not Reg-RWS
        # Placeholder for future implementation
        return None

    def sync_resources(self, account: RIRAccount, resource_type: str | None = None) -> list[dict[str, Any]]:
        """Sync resources from ARIN for the given account."""
        results: list[dict[str, Any]] = []
        # Implementation will be filled in when sync logic is built (Task 12)
        return results

    def _poc_to_dict(self, poc) -> dict[str, Any]:
        """Convert a pyregrws Poc model to a dict."""
        return {
            "handle": poc.handle,
            "contact_type": poc.contact_type,
            "first_name": getattr(poc, "first_name", "") or "",
            "last_name": poc.last_name or "",
            "company_name": getattr(poc, "company_name", "") or "",
            "city": getattr(poc, "city", "") or "",
            "postal_code": getattr(poc, "postal_code", "") or "",
            "country": getattr(poc, "iso3166_1", {}).get("code2", "") if isinstance(getattr(poc, "iso3166_1", None), dict) else "",
            "raw_data": self._safe_serialize(poc),
        }

    def _org_to_dict(self, org) -> dict[str, Any]:
        """Convert a pyregrws Org model to a dict."""
        street = ""
        if hasattr(org, "street_address") and org.street_address:
            street = "\n".join(
                line.line for line in org.street_address if hasattr(line, "line") and line.line
            )
        return {
            "handle": org.handle,
            "name": org.org_name or "",
            "street_address": street,
            "city": getattr(org, "city", "") or "",
            "state_province": getattr(org, "iso3166_2", "") or "",
            "postal_code": getattr(org, "postal_code", "") or "",
            "country": getattr(org, "iso3166_1", {}).get("code2", "") if isinstance(getattr(org, "iso3166_1", None), dict) else "",
            "raw_data": self._safe_serialize(org),
        }

    def _net_to_dict(self, net) -> dict[str, Any]:
        """Convert a pyregrws Net model to a dict."""
        net_blocks = []
        if hasattr(net, "net_blocks") and net.net_blocks:
            for block in net.net_blocks:
                net_blocks.append({
                    "start_address": str(getattr(block, "start_address", "")),
                    "end_address": str(getattr(block, "end_address", "")),
                    "cidr_length": getattr(block, "cidr_length", None),
                    "type": getattr(block, "type", ""),
                })
        return {
            "handle": net.handle,
            "net_name": net.net_name or "",
            "version": getattr(net, "version", None),
            "org_handle": getattr(net, "org_handle", "") or "",
            "parent_net_handle": getattr(net, "parent_net_handle", "") or "",
            "net_blocks": net_blocks,
            "raw_data": self._safe_serialize(net),
        }

    def _safe_serialize(self, obj) -> dict:
        """Safely serialize a pyregrws model to a JSON-safe dict."""
        try:
            if hasattr(obj, "dict"):
                return obj.dict()
            return {}
        except Exception:
            return {}
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_backends/test_arin.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add netbox_rir_manager/backends/arin.py tests/test_backends/test_arin.py
git commit -m "feat: add ARIN backend using pyregrws"
```

---

## Task 5: Test Infrastructure (conftest.py) -- COMPLETED

**Files:**
- Create: `tests/conftest.py`
- Create: `.devcontainer/devcontainer.json`
- Create: `.devcontainer/docker-compose.yml`
- Create: `.devcontainer/Dockerfile-plugin_dev`
- Create: `.devcontainer/entrypoint-dev.sh`
- Create: `.devcontainer/configuration/configuration.py`
- Create: `.devcontainer/configuration/plugins.py`
- Create: `.devcontainer/env/netbox.env`
- Create: `.devcontainer/env/postgres.env`
- Create: `.devcontainer/env/redis.env`
- Create: `.devcontainer/requirements-dev.txt`

**Step 1: Create conftest.py**

Create `tests/conftest.py` (following netbox-notices pattern):

```python
"""
Pytest configuration for netbox_rir_manager tests.
Sets up Django and NetBox environment for testing.
"""

import os
import sys

import pytest

# Add NetBox to Python path BEFORE any imports
netbox_path = os.environ.get("PYTHONPATH", "/opt/netbox/netbox")
if netbox_path not in sys.path:
    sys.path.insert(0, netbox_path)

os.environ["DJANGO_SETTINGS_MODULE"] = "netbox.settings"

is_ci = "GITHUB_ACTIONS" in os.environ

if not is_ci:
    os.environ.setdefault("NETBOX_CONFIGURATION", "netbox.configuration_testing")

    from netbox import configuration_testing

    configuration_testing.DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "netbox"),
            "USER": os.environ.get("DB_USER", "netbox"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "postgres"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": 300,
        }
    }

    configuration_testing.REDIS = {
        "tasks": {
            "HOST": os.environ.get("REDIS_HOST", "redis"),
            "PORT": int(os.environ.get("REDIS_PORT", 6379)),
            "PASSWORD": os.environ.get("REDIS_PASSWORD", ""),
            "DATABASE": int(os.environ.get("REDIS_DATABASE", 0)),
            "SSL": os.environ.get("REDIS_SSL", "False").lower() == "true",
        },
        "caching": {
            "HOST": os.environ.get("REDIS_CACHE_HOST", os.environ.get("REDIS_HOST", "redis")),
            "PORT": int(os.environ.get("REDIS_CACHE_PORT", os.environ.get("REDIS_PORT", 6379))),
            "PASSWORD": os.environ.get("REDIS_CACHE_PASSWORD", os.environ.get("REDIS_PASSWORD", "")),
            "DATABASE": int(os.environ.get("REDIS_CACHE_DATABASE", 1)),
            "SSL": os.environ.get("REDIS_CACHE_SSL", os.environ.get("REDIS_SSL", "False")).lower() == "true",
        },
    }

    if not hasattr(configuration_testing, "PLUGINS"):
        configuration_testing.PLUGINS = []
    if "netbox_rir_manager" not in configuration_testing.PLUGINS:
        configuration_testing.PLUGINS.append("netbox_rir_manager")

    if not hasattr(configuration_testing, "PLUGINS_CONFIG"):
        configuration_testing.PLUGINS_CONFIG = {}
    if "netbox_rir_manager" not in configuration_testing.PLUGINS_CONFIG:
        configuration_testing.PLUGINS_CONFIG["netbox_rir_manager"] = {}

import django  # noqa: E402

django.setup()


def pytest_configure(config):
    pass


@pytest.fixture
def rir(db):
    """Create a test RIR (ARIN)."""
    from ipam.models import RIR

    return RIR.objects.create(name="ARIN", slug="arin", is_private=False)


@pytest.fixture
def rir_account(db, rir):
    """Create a test RIR account."""
    from netbox_rir_manager.models import RIRAccount

    return RIRAccount.objects.create(
        rir=rir,
        name="Test ARIN Account",
        api_key="test-api-key-12345",
        org_handle="TESTORG-ARIN",
        is_active=True,
    )
```

**Step 2: Create devcontainer setup**

Create all devcontainer files following the netbox-notices pattern but adapted for this plugin. Key differences:
- Container name: `netbox-rir-manager-devcontainer`
- Workspace folder: `/opt/netbox-rir-manager`
- Plugin name: `netbox_rir_manager`
- NetBox version: v4.5.x compatible image

See netbox-notices devcontainer files as exact template, substituting:
- `netbox-notices` -> `netbox-rir-manager`
- `notices` -> `netbox_rir_manager`
- NetBox variant ARG updated to v4.5.x

**Step 3: Commit**

```bash
git add tests/conftest.py .devcontainer/
git commit -m "feat: add test infrastructure and devcontainer"
```

---

## Task 6: Django Models - RIRAccount -- COMPLETED (later renamed to RIRConfig in phase 2)

**Files:**
- Create: `netbox_rir_manager/models/__init__.py`
- Create: `netbox_rir_manager/models/accounts.py`
- Create: `netbox_rir_manager/migrations/__init__.py`
- Create: `tests/test_models.py`

**Step 1: Write the failing test**

Create `tests/test_models.py`:

```python
import pytest


@pytest.mark.django_db
class TestRIRAccount:
    def test_create_rir_account(self, rir):
        from netbox_rir_manager.models import RIRAccount

        account = RIRAccount.objects.create(
            rir=rir,
            name="Test Account",
            api_key="secret-key-123",
            org_handle="TESTORG-ARIN",
        )
        assert account.pk is not None
        assert account.name == "Test Account"
        assert account.is_active is True
        assert str(account) == "Test Account"

    def test_rir_account_unique_together(self, rir):
        from django.db import IntegrityError

        from netbox_rir_manager.models import RIRAccount

        RIRAccount.objects.create(rir=rir, name="Unique Account", api_key="key1")
        with pytest.raises(IntegrityError):
            RIRAccount.objects.create(rir=rir, name="Unique Account", api_key="key2")
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py::TestRIRAccount -v
```

Expected: FAIL (model doesn't exist)

**Step 3: Write RIRAccount model**

Create `netbox_rir_manager/models/accounts.py`:

```python
from django.db import models
from django.urls import reverse
from ipam.models import RIR
from netbox.models import NetBoxModel


class RIRAccount(NetBoxModel):
    """Credentials and configuration for RIR API access."""

    rir = models.ForeignKey(RIR, on_delete=models.CASCADE, related_name="rir_accounts")
    name = models.CharField(max_length=100)
    api_key = models.CharField(max_length=255)
    api_url = models.URLField(blank=True, default="")
    org_handle = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["rir", "name"]
        constraints = [
            models.UniqueConstraint(fields=["rir", "name"], name="unique_rir_account_name"),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:riraccount", args=[self.pk])
```

Create `netbox_rir_manager/models/__init__.py`:

```python
from netbox_rir_manager.models.accounts import RIRAccount

__all__ = [
    "RIRAccount",
]
```

Create empty `netbox_rir_manager/migrations/__init__.py`.

**Step 4: Generate and run migration**

```bash
cd /tmp/netbox/netbox  # (in devcontainer)
python manage.py makemigrations netbox_rir_manager
python manage.py migrate
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_models.py::TestRIRAccount -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add netbox_rir_manager/models/ netbox_rir_manager/migrations/
git commit -m "feat: add RIRAccount model"
```

---

## Task 7: Django Models - RIROrganization, RIRContact, RIRNetwork -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/models/resources.py`
- Modify: `netbox_rir_manager/models/__init__.py`
- Modify: `tests/test_models.py`

**Step 1: Write failing tests**

Add to `tests/test_models.py`:

```python
@pytest.mark.django_db
class TestRIROrganization:
    def test_create_rir_organization(self, rir_account):
        from netbox_rir_manager.models import RIROrganization

        org = RIROrganization.objects.create(
            account=rir_account,
            handle="EXAMPLE-ARIN",
            name="Example Corp",
            city="Anytown",
            country="US",
        )
        assert org.pk is not None
        assert str(org) == "EXAMPLE-ARIN"

    def test_rir_organization_unique_handle(self, rir_account):
        from django.db import IntegrityError

        from netbox_rir_manager.models import RIROrganization

        RIROrganization.objects.create(account=rir_account, handle="DUP-ARIN", name="Org 1")
        with pytest.raises(IntegrityError):
            RIROrganization.objects.create(account=rir_account, handle="DUP-ARIN", name="Org 2")


@pytest.mark.django_db
class TestRIRContact:
    def test_create_rir_contact(self, rir_account):
        from netbox_rir_manager.models import RIRContact

        contact = RIRContact.objects.create(
            account=rir_account,
            handle="JD123-ARIN",
            contact_type="PERSON",
            first_name="John",
            last_name="Doe",
            email="jdoe@example.com",
        )
        assert contact.pk is not None
        assert str(contact) == "JD123-ARIN"


@pytest.mark.django_db
class TestRIRNetwork:
    def test_create_rir_network(self, rir_account):
        from netbox_rir_manager.models import RIRNetwork

        net = RIRNetwork.objects.create(
            account=rir_account,
            handle="NET-192-0-2-0-1",
            net_name="EXAMPLE-NET",
        )
        assert net.pk is not None
        assert str(net) == "NET-192-0-2-0-1"

    def test_rir_network_link_to_aggregate(self, rir_account, rir):
        from ipam.models import Aggregate

        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
        net = RIRNetwork.objects.create(
            account=rir_account,
            handle="NET-192-0-2-0-1",
            net_name="EXAMPLE-NET",
            aggregate=agg,
        )
        assert net.aggregate == agg
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_models.py -v
```

**Step 3: Write resource models**

Create `netbox_rir_manager/models/resources.py`:

```python
from django.db import models
from django.urls import reverse
from ipam.models import Aggregate, Prefix
from netbox.models import NetBoxModel


class RIROrganization(NetBoxModel):
    """Organization record from RIR."""

    account = models.ForeignKey(
        "netbox_rir_manager.RIRAccount",
        on_delete=models.CASCADE,
        related_name="organizations",
    )
    handle = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    street_address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state_province = models.CharField(max_length=100, blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    country = models.CharField(max_length=2, blank=True, default="")
    raw_data = models.JSONField(default=dict, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["handle"]

    def __str__(self):
        return self.handle

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirorganization", args=[self.pk])


class RIRContact(NetBoxModel):
    """Point of Contact record from RIR."""

    account = models.ForeignKey(
        "netbox_rir_manager.RIRAccount",
        on_delete=models.CASCADE,
        related_name="contacts",
    )
    handle = models.CharField(max_length=50, unique=True)
    contact_type = models.CharField(max_length=20)  # PERSON or ROLE
    first_name = models.CharField(max_length=100, blank=True, default="")
    last_name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    organization = models.ForeignKey(
        RIROrganization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
    )
    raw_data = models.JSONField(default=dict, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["handle"]

    def __str__(self):
        return self.handle

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rircontact", args=[self.pk])


class RIRNetwork(NetBoxModel):
    """Network allocation record from RIR, linked to NetBox Aggregates/Prefixes."""

    account = models.ForeignKey(
        "netbox_rir_manager.RIRAccount",
        on_delete=models.CASCADE,
        related_name="networks",
    )
    handle = models.CharField(max_length=50, unique=True)
    net_name = models.CharField(max_length=100)
    organization = models.ForeignKey(
        RIROrganization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="networks",
    )
    aggregate = models.ForeignKey(
        Aggregate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rir_networks",
    )
    prefix = models.ForeignKey(
        Prefix,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rir_networks",
    )
    raw_data = models.JSONField(default=dict, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["handle"]

    def __str__(self):
        return self.handle

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirnetwork", args=[self.pk])
```

Update `netbox_rir_manager/models/__init__.py`:

```python
from netbox_rir_manager.models.accounts import RIRAccount
from netbox_rir_manager.models.resources import RIRContact, RIRNetwork, RIROrganization

__all__ = [
    "RIRAccount",
    "RIRContact",
    "RIRNetwork",
    "RIROrganization",
]
```

**Step 4: Generate migration and run tests**

```bash
python manage.py makemigrations netbox_rir_manager
python manage.py migrate
pytest tests/test_models.py -v
```

**Step 5: Commit**

```bash
git add netbox_rir_manager/models/ netbox_rir_manager/migrations/ tests/test_models.py
git commit -m "feat: add RIROrganization, RIRContact, RIRNetwork models"
```

---

## Task 8: Django Models - RIRSyncLog -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/models/sync.py`
- Modify: `netbox_rir_manager/models/__init__.py`
- Create: `netbox_rir_manager/choices.py`
- Modify: `tests/test_models.py`

**Step 1: Write failing test**

Add to `tests/test_models.py`:

```python
@pytest.mark.django_db
class TestRIRSyncLog:
    def test_create_sync_log(self, rir_account):
        from netbox_rir_manager.models import RIRSyncLog

        log = RIRSyncLog.objects.create(
            account=rir_account,
            operation="sync",
            object_type="organization",
            object_handle="EXAMPLE-ARIN",
            status="success",
            message="Synced successfully",
        )
        assert log.pk is not None
        assert str(log) == "sync EXAMPLE-ARIN (success)"
```

**Step 2: Run test to verify it fails**

**Step 3: Create choices and sync log model**

Create `netbox_rir_manager/choices.py`:

```python
from utilities.choices import ChoiceSet


class SyncOperationChoices(ChoiceSet):
    key = "RIRSyncLog.operation"

    CHOICES = [
        ("sync", "Sync", "blue"),
        ("create", "Create", "green"),
        ("update", "Update", "yellow"),
        ("delete", "Delete", "red"),
    ]


class SyncStatusChoices(ChoiceSet):
    key = "RIRSyncLog.status"

    CHOICES = [
        ("success", "Success", "green"),
        ("error", "Error", "red"),
        ("skipped", "Skipped", "gray"),
    ]


class ContactTypeChoices(ChoiceSet):
    key = "RIRContact.contact_type"

    CHOICES = [
        ("PERSON", "Person", "blue"),
        ("ROLE", "Role", "purple"),
    ]
```

Create `netbox_rir_manager/models/sync.py`:

```python
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel

from netbox_rir_manager.choices import SyncOperationChoices, SyncStatusChoices


class RIRSyncLog(NetBoxModel):
    """Audit log for sync operations."""

    account = models.ForeignKey(
        "netbox_rir_manager.RIRAccount",
        on_delete=models.CASCADE,
        related_name="sync_logs",
    )
    operation = models.CharField(max_length=50, choices=SyncOperationChoices)
    object_type = models.CharField(max_length=50)
    object_handle = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=SyncStatusChoices)
    message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.operation} {self.object_handle} ({self.status})"

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirsynclog", args=[self.pk])
```

Update `netbox_rir_manager/models/__init__.py` to include `RIRSyncLog`.

**Step 4: Generate migration and run tests**

**Step 5: Commit**

```bash
git add netbox_rir_manager/choices.py netbox_rir_manager/models/ netbox_rir_manager/migrations/ tests/test_models.py
git commit -m "feat: add RIRSyncLog model and choice sets"
```

---

## Task 9: Tables -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/tables.py`

**Step 1: Write tables**

Create `netbox_rir_manager/tables.py`:

```python
import django_tables2 as tables
from netbox.tables import NetBoxTable, columns

from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog


class RIRAccountTable(NetBoxTable):
    name = tables.Column(linkify=True)
    rir = tables.Column(linkify=True)
    is_active = columns.BooleanColumn()
    last_sync = columns.DateTimeColumn()

    class Meta(NetBoxTable.Meta):
        model = RIRAccount
        fields = ("pk", "id", "name", "rir", "org_handle", "is_active", "last_sync")
        default_columns = ("name", "rir", "org_handle", "is_active", "last_sync")


class RIROrganizationTable(NetBoxTable):
    handle = tables.Column(linkify=True)
    name = tables.Column()
    account = tables.Column(linkify=True)
    city = tables.Column()
    country = tables.Column()
    last_synced = columns.DateTimeColumn()

    class Meta(NetBoxTable.Meta):
        model = RIROrganization
        fields = ("pk", "id", "handle", "name", "account", "city", "country", "last_synced")
        default_columns = ("handle", "name", "account", "city", "country", "last_synced")


class RIRContactTable(NetBoxTable):
    handle = tables.Column(linkify=True)
    last_name = tables.Column()
    first_name = tables.Column()
    contact_type = tables.Column()
    company_name = tables.Column()
    email = tables.Column()
    organization = tables.Column(linkify=True)
    last_synced = columns.DateTimeColumn()

    class Meta(NetBoxTable.Meta):
        model = RIRContact
        fields = (
            "pk", "id", "handle", "contact_type", "first_name", "last_name",
            "company_name", "email", "organization", "last_synced",
        )
        default_columns = ("handle", "contact_type", "first_name", "last_name", "email", "organization")


class RIRNetworkTable(NetBoxTable):
    handle = tables.Column(linkify=True)
    net_name = tables.Column()
    organization = tables.Column(linkify=True)
    aggregate = tables.Column(linkify=True)
    prefix = tables.Column(linkify=True)
    last_synced = columns.DateTimeColumn()

    class Meta(NetBoxTable.Meta):
        model = RIRNetwork
        fields = (
            "pk", "id", "handle", "net_name", "organization",
            "aggregate", "prefix", "last_synced",
        )
        default_columns = ("handle", "net_name", "organization", "aggregate", "prefix", "last_synced")


class RIRSyncLogTable(NetBoxTable):
    account = tables.Column(linkify=True)
    operation = tables.Column()
    object_type = tables.Column()
    object_handle = tables.Column()
    status = tables.Column()
    message = tables.Column()

    class Meta(NetBoxTable.Meta):
        model = RIRSyncLog
        fields = ("pk", "id", "account", "operation", "object_type", "object_handle", "status", "message", "created")
        default_columns = ("account", "operation", "object_type", "object_handle", "status", "created")
```

**Step 2: Commit**

```bash
git add netbox_rir_manager/tables.py
git commit -m "feat: add tables for all models"
```

---

## Task 10: Filtersets and Forms -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/filtersets.py`
- Create: `netbox_rir_manager/forms.py`

**Step 1: Write filtersets**

Create `netbox_rir_manager/filtersets.py`:

```python
import django_filters
from ipam.models import RIR
from netbox.filtersets import NetBoxModelFilterSet

from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog


class RIRAccountFilterSet(NetBoxModelFilterSet):
    rir_id = django_filters.ModelMultipleChoiceFilter(queryset=RIR.objects.all(), label="RIR")
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = RIRAccount
        fields = ("id", "name", "rir_id", "is_active", "org_handle")

    def search(self, queryset, name, value):
        return queryset.filter(name__icontains=value)


class RIROrganizationFilterSet(NetBoxModelFilterSet):
    account_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIRAccount.objects.all(), label="Account"
    )

    class Meta:
        model = RIROrganization
        fields = ("id", "handle", "name", "account_id", "country")

    def search(self, queryset, name, value):
        return queryset.filter(handle__icontains=value) | queryset.filter(name__icontains=value)


class RIRContactFilterSet(NetBoxModelFilterSet):
    account_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIRAccount.objects.all(), label="Account"
    )
    contact_type = django_filters.CharFilter()
    organization_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIROrganization.objects.all(), label="Organization"
    )

    class Meta:
        model = RIRContact
        fields = ("id", "handle", "contact_type", "account_id", "organization_id")

    def search(self, queryset, name, value):
        return queryset.filter(handle__icontains=value) | queryset.filter(last_name__icontains=value)


class RIRNetworkFilterSet(NetBoxModelFilterSet):
    account_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIRAccount.objects.all(), label="Account"
    )
    organization_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIROrganization.objects.all(), label="Organization"
    )

    class Meta:
        model = RIRNetwork
        fields = ("id", "handle", "net_name", "account_id", "organization_id")

    def search(self, queryset, name, value):
        return queryset.filter(handle__icontains=value) | queryset.filter(net_name__icontains=value)


class RIRSyncLogFilterSet(NetBoxModelFilterSet):
    account_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIRAccount.objects.all(), label="Account"
    )
    operation = django_filters.CharFilter()
    status = django_filters.CharFilter()

    class Meta:
        model = RIRSyncLog
        fields = ("id", "account_id", "operation", "status", "object_type")

    def search(self, queryset, name, value):
        return queryset.filter(object_handle__icontains=value) | queryset.filter(message__icontains=value)
```

**Step 2: Write forms**

Create `netbox_rir_manager/forms.py`:

```python
from django import forms
from ipam.models import RIR
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from utilities.forms.rendering import FieldSet

from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization


class RIRAccountForm(NetBoxModelForm):
    rir = DynamicModelChoiceField(queryset=RIR.objects.all())

    fieldsets = (
        FieldSet("rir", "name", "api_key", "api_url", "org_handle", "is_active", name="RIR Account"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIRAccount
        fields = ("rir", "name", "api_key", "api_url", "org_handle", "is_active", "tags")
        widgets = {
            "api_key": forms.PasswordInput(render_value=True),
        }


class RIRAccountFilterForm(NetBoxModelFilterSetForm):
    model = RIRAccount
    rir_id = DynamicModelMultipleChoiceField(queryset=RIR.objects.all(), required=False, label="RIR")
    is_active = forms.NullBooleanField(required=False)


class RIROrganizationForm(NetBoxModelForm):
    account = DynamicModelChoiceField(queryset=RIRAccount.objects.all())

    fieldsets = (
        FieldSet("account", "handle", "name", name="Organization"),
        FieldSet("street_address", "city", "state_province", "postal_code", "country", name="Address"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIROrganization
        fields = (
            "account", "handle", "name", "street_address", "city",
            "state_province", "postal_code", "country", "tags",
        )


class RIROrganizationFilterForm(NetBoxModelFilterSetForm):
    model = RIROrganization
    account_id = DynamicModelMultipleChoiceField(queryset=RIRAccount.objects.all(), required=False, label="Account")
    country = forms.CharField(required=False)


class RIRContactForm(NetBoxModelForm):
    account = DynamicModelChoiceField(queryset=RIRAccount.objects.all())
    organization = DynamicModelChoiceField(queryset=RIROrganization.objects.all(), required=False)

    fieldsets = (
        FieldSet("account", "handle", "contact_type", name="Contact"),
        FieldSet("first_name", "last_name", "company_name", "email", "phone", name="Details"),
        FieldSet("organization", name="Organization"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIRContact
        fields = (
            "account", "handle", "contact_type", "first_name", "last_name",
            "company_name", "email", "phone", "organization", "tags",
        )


class RIRContactFilterForm(NetBoxModelFilterSetForm):
    model = RIRContact
    account_id = DynamicModelMultipleChoiceField(queryset=RIRAccount.objects.all(), required=False, label="Account")
    contact_type = forms.CharField(required=False)
    organization_id = DynamicModelMultipleChoiceField(
        queryset=RIROrganization.objects.all(), required=False, label="Organization"
    )


class RIRNetworkForm(NetBoxModelForm):
    account = DynamicModelChoiceField(queryset=RIRAccount.objects.all())
    organization = DynamicModelChoiceField(queryset=RIROrganization.objects.all(), required=False)

    fieldsets = (
        FieldSet("account", "handle", "net_name", "organization", name="Network"),
        FieldSet("aggregate", "prefix", name="NetBox Links"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIRNetwork
        fields = ("account", "handle", "net_name", "organization", "aggregate", "prefix", "tags")


class RIRNetworkFilterForm(NetBoxModelFilterSetForm):
    model = RIRNetwork
    account_id = DynamicModelMultipleChoiceField(queryset=RIRAccount.objects.all(), required=False, label="Account")
    organization_id = DynamicModelMultipleChoiceField(
        queryset=RIROrganization.objects.all(), required=False, label="Organization"
    )
```

**Step 3: Commit**

```bash
git add netbox_rir_manager/filtersets.py netbox_rir_manager/forms.py
git commit -m "feat: add filtersets and forms for all models"
```

---

## Task 11: Views and URL Configuration -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/views.py`
- Create: `netbox_rir_manager/urls.py`

**Step 1: Write views**

Create `netbox_rir_manager/views.py` with standard NetBox generic views for each model:

```python
from netbox.views import generic

from netbox_rir_manager.filtersets import (
    RIRAccountFilterSet,
    RIRContactFilterSet,
    RIRNetworkFilterSet,
    RIROrganizationFilterSet,
    RIRSyncLogFilterSet,
)
from netbox_rir_manager.forms import (
    RIRAccountFilterForm,
    RIRAccountForm,
    RIRContactFilterForm,
    RIRContactForm,
    RIRNetworkFilterForm,
    RIRNetworkForm,
    RIROrganizationFilterForm,
    RIROrganizationForm,
)
from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog
from netbox_rir_manager.tables import (
    RIRAccountTable,
    RIRContactTable,
    RIRNetworkTable,
    RIROrganizationTable,
    RIRSyncLogTable,
)


# --- RIRAccount Views ---
class RIRAccountListView(generic.ObjectListView):
    queryset = RIRAccount.objects.all()
    table = RIRAccountTable
    filterset = RIRAccountFilterSet
    filterset_form = RIRAccountFilterForm


class RIRAccountView(generic.ObjectView):
    queryset = RIRAccount.objects.all()


class RIRAccountEditView(generic.ObjectEditView):
    queryset = RIRAccount.objects.all()
    form = RIRAccountForm


class RIRAccountDeleteView(generic.ObjectDeleteView):
    queryset = RIRAccount.objects.all()


# --- RIROrganization Views ---
class RIROrganizationListView(generic.ObjectListView):
    queryset = RIROrganization.objects.all()
    table = RIROrganizationTable
    filterset = RIROrganizationFilterSet
    filterset_form = RIROrganizationFilterForm


class RIROrganizationView(generic.ObjectView):
    queryset = RIROrganization.objects.all()


class RIROrganizationEditView(generic.ObjectEditView):
    queryset = RIROrganization.objects.all()
    form = RIROrganizationForm


class RIROrganizationDeleteView(generic.ObjectDeleteView):
    queryset = RIROrganization.objects.all()


# --- RIRContact Views ---
class RIRContactListView(generic.ObjectListView):
    queryset = RIRContact.objects.all()
    table = RIRContactTable
    filterset = RIRContactFilterSet
    filterset_form = RIRContactFilterForm


class RIRContactView(generic.ObjectView):
    queryset = RIRContact.objects.all()


class RIRContactEditView(generic.ObjectEditView):
    queryset = RIRContact.objects.all()
    form = RIRContactForm


class RIRContactDeleteView(generic.ObjectDeleteView):
    queryset = RIRContact.objects.all()


# --- RIRNetwork Views ---
class RIRNetworkListView(generic.ObjectListView):
    queryset = RIRNetwork.objects.all()
    table = RIRNetworkTable
    filterset = RIRNetworkFilterSet
    filterset_form = RIRNetworkFilterForm


class RIRNetworkView(generic.ObjectView):
    queryset = RIRNetwork.objects.all()


class RIRNetworkEditView(generic.ObjectEditView):
    queryset = RIRNetwork.objects.all()
    form = RIRNetworkForm


class RIRNetworkDeleteView(generic.ObjectDeleteView):
    queryset = RIRNetwork.objects.all()


# --- RIRSyncLog Views ---
class RIRSyncLogListView(generic.ObjectListView):
    queryset = RIRSyncLog.objects.all()
    table = RIRSyncLogTable
    filterset = RIRSyncLogFilterSet


class RIRSyncLogView(generic.ObjectView):
    queryset = RIRSyncLog.objects.all()


class RIRSyncLogDeleteView(generic.ObjectDeleteView):
    queryset = RIRSyncLog.objects.all()
```

**Step 2: Write URL configuration**

Create `netbox_rir_manager/urls.py`:

```python
from django.urls import path
from netbox.views.generic import ObjectChangeLogView

from netbox_rir_manager import views
from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog

urlpatterns = [
    # RIRAccount
    path("accounts/", views.RIRAccountListView.as_view(), name="riraccount_list"),
    path("accounts/add/", views.RIRAccountEditView.as_view(), name="riraccount_add"),
    path("accounts/<int:pk>/", views.RIRAccountView.as_view(), name="riraccount"),
    path("accounts/<int:pk>/edit/", views.RIRAccountEditView.as_view(), name="riraccount_edit"),
    path("accounts/<int:pk>/delete/", views.RIRAccountDeleteView.as_view(), name="riraccount_delete"),
    path(
        "accounts/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="riraccount_changelog",
        kwargs={"model": RIRAccount},
    ),
    # RIROrganization
    path("organizations/", views.RIROrganizationListView.as_view(), name="rirorganization_list"),
    path("organizations/add/", views.RIROrganizationEditView.as_view(), name="rirorganization_add"),
    path("organizations/<int:pk>/", views.RIROrganizationView.as_view(), name="rirorganization"),
    path("organizations/<int:pk>/edit/", views.RIROrganizationEditView.as_view(), name="rirorganization_edit"),
    path("organizations/<int:pk>/delete/", views.RIROrganizationDeleteView.as_view(), name="rirorganization_delete"),
    path(
        "organizations/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rirorganization_changelog",
        kwargs={"model": RIROrganization},
    ),
    # RIRContact
    path("contacts/", views.RIRContactListView.as_view(), name="rircontact_list"),
    path("contacts/add/", views.RIRContactEditView.as_view(), name="rircontact_add"),
    path("contacts/<int:pk>/", views.RIRContactView.as_view(), name="rircontact"),
    path("contacts/<int:pk>/edit/", views.RIRContactEditView.as_view(), name="rircontact_edit"),
    path("contacts/<int:pk>/delete/", views.RIRContactDeleteView.as_view(), name="rircontact_delete"),
    path(
        "contacts/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rircontact_changelog",
        kwargs={"model": RIRContact},
    ),
    # RIRNetwork
    path("networks/", views.RIRNetworkListView.as_view(), name="rirnetwork_list"),
    path("networks/add/", views.RIRNetworkEditView.as_view(), name="rirnetwork_add"),
    path("networks/<int:pk>/", views.RIRNetworkView.as_view(), name="rirnetwork"),
    path("networks/<int:pk>/edit/", views.RIRNetworkEditView.as_view(), name="rirnetwork_edit"),
    path("networks/<int:pk>/delete/", views.RIRNetworkDeleteView.as_view(), name="rirnetwork_delete"),
    path(
        "networks/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rirnetwork_changelog",
        kwargs={"model": RIRNetwork},
    ),
    # RIRSyncLog
    path("sync-logs/", views.RIRSyncLogListView.as_view(), name="rirsynclog_list"),
    path("sync-logs/<int:pk>/", views.RIRSyncLogView.as_view(), name="rirsynclog"),
    path("sync-logs/<int:pk>/delete/", views.RIRSyncLogDeleteView.as_view(), name="rirsynclog_delete"),
    path(
        "sync-logs/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rirsynclog_changelog",
        kwargs={"model": RIRSyncLog},
    ),
]
```

**Step 3: Commit**

```bash
git add netbox_rir_manager/views.py netbox_rir_manager/urls.py
git commit -m "feat: add views and URL configuration"
```

---

## Task 12: Templates -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/templates/netbox_rir_manager/riraccount.html`
- Create: `netbox_rir_manager/templates/netbox_rir_manager/rirorganization.html`
- Create: `netbox_rir_manager/templates/netbox_rir_manager/rircontact.html`
- Create: `netbox_rir_manager/templates/netbox_rir_manager/rirnetwork.html`
- Create: `netbox_rir_manager/templates/netbox_rir_manager/rirsynclog.html`

**Step 1: Create detail templates**

Each template extends `generic/object.html` and renders model-specific fields in panels. Follow the NetBox plugin convention of using `{% block content %}` with card/table layouts.

Example `riraccount.html`:

```html
{% extends 'generic/object.html' %}
{% load helpers %}
{% load plugins %}

{% block content %}
<div class="row mb-3">
    <div class="col col-md-6">
        <div class="card">
            <h5 class="card-header">RIR Account</h5>
            <table class="table table-hover attr-table">
                <tr>
                    <th scope="row">RIR</th>
                    <td>{{ object.rir|linkify }}</td>
                </tr>
                <tr>
                    <th scope="row">Name</th>
                    <td>{{ object.name }}</td>
                </tr>
                <tr>
                    <th scope="row">Org Handle</th>
                    <td>{{ object.org_handle|placeholder }}</td>
                </tr>
                <tr>
                    <th scope="row">API URL</th>
                    <td>{{ object.api_url|placeholder }}</td>
                </tr>
                <tr>
                    <th scope="row">Active</th>
                    <td>{% checkmark object.is_active %}</td>
                </tr>
                <tr>
                    <th scope="row">Last Sync</th>
                    <td>{{ object.last_sync|placeholder }}</td>
                </tr>
            </table>
        </div>
        {% plugin_left_page object %}
    </div>
    <div class="col col-md-6">
        {% include 'inc/panels/tags.html' %}
        {% plugin_right_page object %}
    </div>
</div>
<div class="row">
    <div class="col col-md-12">
        {% plugin_full_width_page object %}
    </div>
</div>
{% endblock content %}
```

Create similar templates for each model (rirorganization.html, rircontact.html, rirnetwork.html, rirsynclog.html), each showing the relevant fields in the same card/table pattern.

**Step 2: Commit**

```bash
git add netbox_rir_manager/templates/
git commit -m "feat: add detail view templates"
```

---

## Task 13: Navigation -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/navigation.py`

**Step 1: Write navigation**

Create `netbox_rir_manager/navigation.py`:

```python
from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem

menu = PluginMenu(
    label="RIR Manager",
    groups=(
        (
            "Accounts",
            (
                PluginMenuItem(
                    link="plugins:netbox_rir_manager:riraccount_list",
                    link_text="RIR Accounts",
                    permissions=["netbox_rir_manager.view_riraccount"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:netbox_rir_manager:riraccount_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=["netbox_rir_manager.add_riraccount"],
                        ),
                    ),
                ),
            ),
        ),
        (
            "Resources",
            (
                PluginMenuItem(
                    link="plugins:netbox_rir_manager:rirorganization_list",
                    link_text="Organizations",
                    permissions=["netbox_rir_manager.view_rirorganization"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:netbox_rir_manager:rirorganization_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=["netbox_rir_manager.add_rirorganization"],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:netbox_rir_manager:rircontact_list",
                    link_text="Contacts (POCs)",
                    permissions=["netbox_rir_manager.view_rircontact"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:netbox_rir_manager:rircontact_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=["netbox_rir_manager.add_rircontact"],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:netbox_rir_manager:rirnetwork_list",
                    link_text="Networks",
                    permissions=["netbox_rir_manager.view_rirnetwork"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:netbox_rir_manager:rirnetwork_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=["netbox_rir_manager.add_rirnetwork"],
                        ),
                    ),
                ),
            ),
        ),
        (
            "Operations",
            (
                PluginMenuItem(
                    link="plugins:netbox_rir_manager:rirsynclog_list",
                    link_text="Sync Logs",
                    permissions=["netbox_rir_manager.view_rirsynclog"],
                ),
            ),
        ),
    ),
    icon_class="mdi mdi-earth",
)
```

**Step 2: Commit**

```bash
git add netbox_rir_manager/navigation.py
git commit -m "feat: add plugin navigation menu"
```

---

## Task 14: Search Indexes -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/search.py`

**Step 1: Write search indexes**

Create `netbox_rir_manager/search.py`:

```python
from netbox.search import SearchIndex, register_search

from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization


@register_search
class RIRAccountIndex(SearchIndex):
    model = RIRAccount
    fields = (
        ("name", 100),
        ("org_handle", 150),
    )


@register_search
class RIROrganizationIndex(SearchIndex):
    model = RIROrganization
    fields = (
        ("handle", 100),
        ("name", 200),
    )


@register_search
class RIRContactIndex(SearchIndex):
    model = RIRContact
    fields = (
        ("handle", 100),
        ("last_name", 200),
        ("first_name", 200),
        ("email", 300),
    )


@register_search
class RIRNetworkIndex(SearchIndex):
    model = RIRNetwork
    fields = (
        ("handle", 100),
        ("net_name", 200),
    )
```

**Step 2: Commit**

```bash
git add netbox_rir_manager/search.py
git commit -m "feat: add search indexes"
```

---

## Task 15: REST API -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/api/__init__.py`
- Create: `netbox_rir_manager/api/serializers.py`
- Create: `netbox_rir_manager/api/views.py`
- Create: `netbox_rir_manager/api/urls.py`
- Create: `tests/test_api.py`

**Step 1: Write failing test**

Create `tests/test_api.py`:

```python
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestRIRAccountAPI:
    def test_list_accounts(self, admin_client, rir_account):
        url = reverse("plugins-api:netbox_rir_manager-api:riraccount-list")
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    def test_get_account(self, admin_client, rir_account):
        url = reverse("plugins-api:netbox_rir_manager-api:riraccount-detail", args=[rir_account.pk])
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == rir_account.name

    def test_api_key_not_in_response(self, admin_client, rir_account):
        url = reverse("plugins-api:netbox_rir_manager-api:riraccount-detail", args=[rir_account.pk])
        response = admin_client.get(url)
        assert "api_key" not in response.json()
```

Add `admin_client` fixture to `conftest.py`:

```python
@pytest.fixture
def admin_client(db):
    """Create an admin user and return a DRF API client."""
    from django.contrib.auth.models import User
    from rest_framework.test import APIClient

    user = User.objects.create_superuser("admin", "admin@example.com", "password")
    client = APIClient()
    client.force_authenticate(user=user)
    return client
```

**Step 2: Run test to verify it fails**

**Step 3: Write API layer**

Create `netbox_rir_manager/api/serializers.py`:

```python
from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers

from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog


class RIRAccountSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_rir_manager-api:riraccount-detail"
    )

    class Meta:
        model = RIRAccount
        fields = (
            "id", "url", "display", "rir", "name", "api_url",
            "org_handle", "is_active", "last_sync",
            "tags", "created", "last_updated",
        )


class RIROrganizationSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_rir_manager-api:rirorganization-detail"
    )

    class Meta:
        model = RIROrganization
        fields = (
            "id", "url", "display", "account", "handle", "name",
            "street_address", "city", "state_province", "postal_code",
            "country", "raw_data", "last_synced",
            "tags", "created", "last_updated",
        )


class RIRContactSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_rir_manager-api:rircontact-detail"
    )

    class Meta:
        model = RIRContact
        fields = (
            "id", "url", "display", "account", "handle", "contact_type",
            "first_name", "last_name", "company_name", "email", "phone",
            "organization", "raw_data", "last_synced",
            "tags", "created", "last_updated",
        )


class RIRNetworkSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_rir_manager-api:rirnetwork-detail"
    )

    class Meta:
        model = RIRNetwork
        fields = (
            "id", "url", "display", "account", "handle", "net_name",
            "organization", "aggregate", "prefix",
            "raw_data", "last_synced",
            "tags", "created", "last_updated",
        )


class RIRSyncLogSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_rir_manager-api:rirsynclog-detail"
    )

    class Meta:
        model = RIRSyncLog
        fields = (
            "id", "url", "display", "account", "operation", "object_type",
            "object_handle", "status", "message",
            "tags", "created", "last_updated",
        )
```

Create `netbox_rir_manager/api/views.py`:

```python
from netbox.api.viewsets import NetBoxModelViewSet

from netbox_rir_manager.api.serializers import (
    RIRAccountSerializer,
    RIRContactSerializer,
    RIRNetworkSerializer,
    RIROrganizationSerializer,
    RIRSyncLogSerializer,
)
from netbox_rir_manager.filtersets import (
    RIRAccountFilterSet,
    RIRContactFilterSet,
    RIRNetworkFilterSet,
    RIROrganizationFilterSet,
    RIRSyncLogFilterSet,
)
from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog


class RIRAccountViewSet(NetBoxModelViewSet):
    queryset = RIRAccount.objects.prefetch_related("tags")
    serializer_class = RIRAccountSerializer
    filterset_class = RIRAccountFilterSet


class RIROrganizationViewSet(NetBoxModelViewSet):
    queryset = RIROrganization.objects.prefetch_related("tags")
    serializer_class = RIROrganizationSerializer
    filterset_class = RIROrganizationFilterSet


class RIRContactViewSet(NetBoxModelViewSet):
    queryset = RIRContact.objects.prefetch_related("tags")
    serializer_class = RIRContactSerializer
    filterset_class = RIRContactFilterSet


class RIRNetworkViewSet(NetBoxModelViewSet):
    queryset = RIRNetwork.objects.prefetch_related("tags")
    serializer_class = RIRNetworkSerializer
    filterset_class = RIRNetworkFilterSet


class RIRSyncLogViewSet(NetBoxModelViewSet):
    queryset = RIRSyncLog.objects.prefetch_related("tags")
    serializer_class = RIRSyncLogSerializer
    filterset_class = RIRSyncLogFilterSet
```

Create `netbox_rir_manager/api/urls.py`:

```python
from netbox.api.routers import NetBoxRouter

from netbox_rir_manager.api import views

router = NetBoxRouter()
router.register("accounts", views.RIRAccountViewSet)
router.register("organizations", views.RIROrganizationViewSet)
router.register("contacts", views.RIRContactViewSet)
router.register("networks", views.RIRNetworkViewSet)
router.register("sync-logs", views.RIRSyncLogViewSet)

urlpatterns = router.urls
```

Create empty `netbox_rir_manager/api/__init__.py`.

**Step 4: Run tests**

```bash
pytest tests/test_api.py -v
```

**Step 5: Commit**

```bash
git add netbox_rir_manager/api/ tests/test_api.py
git commit -m "feat: add REST API serializers, viewsets, and URLs"
```

---

## Task 16: Template Extensions for NetBox IPAM Views -- COMPLETED

**Files:**
- Create: `netbox_rir_manager/template_content.py`
- Create: `netbox_rir_manager/templates/netbox_rir_manager/inc/rir_network_panel.html`

**Step 1: Write template extension**

Create `netbox_rir_manager/template_content.py`:

```python
from netbox.plugins import PluginTemplateExtension

from netbox_rir_manager.models import RIRNetwork


class RIRAggregateExtension(PluginTemplateExtension):
    """Show RIR network info on Aggregate detail page."""

    models = ["ipam.aggregate"]

    def right_page(self):
        obj = self.context["object"]
        rir_networks = RIRNetwork.objects.filter(aggregate=obj)
        return self.render(
            "netbox_rir_manager/inc/rir_network_panel.html",
            extra_context={"rir_networks": rir_networks},
        )


class RIRPrefixExtension(PluginTemplateExtension):
    """Show RIR network info on Prefix detail page."""

    models = ["ipam.prefix"]

    def right_page(self):
        obj = self.context["object"]
        rir_networks = RIRNetwork.objects.filter(prefix=obj)
        return self.render(
            "netbox_rir_manager/inc/rir_network_panel.html",
            extra_context={"rir_networks": rir_networks},
        )


template_extensions = [RIRAggregateExtension, RIRPrefixExtension]
```

Create `netbox_rir_manager/templates/netbox_rir_manager/inc/rir_network_panel.html`:

```html
{% load helpers %}

{% if rir_networks %}
<div class="card">
    <h5 class="card-header">RIR Networks</h5>
    <table class="table table-hover attr-table">
        <thead>
            <tr>
                <th>Handle</th>
                <th>Net Name</th>
                <th>Organization</th>
                <th>Last Synced</th>
            </tr>
        </thead>
        <tbody>
            {% for net in rir_networks %}
            <tr>
                <td><a href="{{ net.get_absolute_url }}">{{ net.handle }}</a></td>
                <td>{{ net.net_name }}</td>
                <td>
                    {% if net.organization %}
                        <a href="{{ net.organization.get_absolute_url }}">{{ net.organization.handle }}</a>
                    {% else %}
                        {{ ''|placeholder }}
                    {% endif %}
                </td>
                <td>{{ net.last_synced|placeholder }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endif %}
```

**Step 2: Commit**

```bash
git add netbox_rir_manager/template_content.py netbox_rir_manager/templates/netbox_rir_manager/inc/
git commit -m "feat: add template extensions for Aggregate and Prefix views"
```

---

## Task 17: Background Sync Jobs -- COMPLETED (expanded in phase 2)

**Files:**
- Create: `netbox_rir_manager/jobs.py`
- Create: `tests/test_jobs.py`

**Step 1: Write failing test**

Create `tests/test_jobs.py`:

```python
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.django_db
class TestRIRSyncJob:
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_creates_log_entries(self, mock_backend_class, rir_account):
        from netbox_rir_manager.jobs import sync_account
        from netbox_rir_manager.models import RIRSyncLog

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = {
            "handle": "TESTORG-ARIN",
            "name": "Test Org",
            "street_address": "",
            "city": "Anytown",
            "state_province": "VA",
            "postal_code": "12345",
            "country": "US",
            "raw_data": {},
        }
        mock_backend_class.from_account.return_value = mock_backend

        sync_account(rir_account, resource_types=["organizations"])

        assert RIRSyncLog.objects.filter(account=rir_account).exists()
```

**Step 2: Run test to verify it fails**

**Step 3: Write sync job**

Create `netbox_rir_manager/jobs.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.utils import timezone

from netbox_rir_manager.backends.arin import ARINBackend
from netbox_rir_manager.models import RIROrganization, RIRSyncLog

if TYPE_CHECKING:
    from netbox_rir_manager.models import RIRAccount

logger = logging.getLogger(__name__)


def sync_account(account: RIRAccount, resource_types: list[str] | None = None) -> list[RIRSyncLog]:
    """
    Sync RIR data for the given account.
    resource_types: list of "organizations", "contacts", "networks". None = all.
    """
    logs: list[RIRSyncLog] = []
    backend = ARINBackend.from_account(account)

    types_to_sync = resource_types or ["organizations", "contacts", "networks"]

    if "organizations" in types_to_sync and account.org_handle:
        logs.extend(_sync_organization(backend, account))

    account.last_sync = timezone.now()
    account.save(update_fields=["last_sync"])

    return logs


def _sync_organization(backend: ARINBackend, account: RIRAccount) -> list[RIRSyncLog]:
    """Sync the primary organization for an account."""
    logs: list[RIRSyncLog] = []

    org_data = backend.get_organization(account.org_handle)
    if org_data is None:
        log = RIRSyncLog.objects.create(
            account=account,
            operation="sync",
            object_type="organization",
            object_handle=account.org_handle,
            status="error",
            message=f"Failed to retrieve organization {account.org_handle}",
        )
        logs.append(log)
        return logs

    org, created = RIROrganization.objects.update_or_create(
        handle=org_data["handle"],
        defaults={
            "account": account,
            "name": org_data.get("name", ""),
            "street_address": org_data.get("street_address", ""),
            "city": org_data.get("city", ""),
            "state_province": org_data.get("state_province", ""),
            "postal_code": org_data.get("postal_code", ""),
            "country": org_data.get("country", ""),
            "raw_data": org_data.get("raw_data", {}),
            "last_synced": timezone.now(),
        },
    )

    log = RIRSyncLog.objects.create(
        account=account,
        operation="sync",
        object_type="organization",
        object_handle=org_data["handle"],
        status="success",
        message=f"{'Created' if created else 'Updated'} organization {org_data['handle']}",
    )
    logs.append(log)

    return logs
```

**Step 4: Run tests**

```bash
pytest tests/test_jobs.py -v
```

**Step 5: Commit**

```bash
git add netbox_rir_manager/jobs.py tests/test_jobs.py
git commit -m "feat: add sync job for RIR account data"
```

---

## Task 18: Signals (placeholder) -- COMPLETED (implemented in phase 2)

**Files:**
- Create: `netbox_rir_manager/signals.py`

**Step 1: Create signals module**

Create `netbox_rir_manager/signals.py`:

```python
# Signal handlers for netbox_rir_manager
# Future: auto-link RIR networks to Aggregates/Prefixes on creation
```

This is a placeholder. The plugin config's `ready()` method imports this module. Actual signal handlers (e.g., auto-matching networks to aggregates) will be added in a later iteration.

**Step 2: Commit**

```bash
git add netbox_rir_manager/signals.py
git commit -m "feat: add signals module placeholder"
```

---

## Task 19: GitHub Actions CI -- COMPLETED

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/publish.yml`

**Step 1: Create CI workflow**

Create `.github/workflows/ci.yml` following the netbox-notices pattern, adapted for this plugin:

```yaml
name: CI Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: netbox
          POSTGRES_USER: netbox
          POSTGRES_PASSWORD: J5brHrAXFLQSif0K
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install NetBox
        run: |
          git clone --depth 1 --branch v4.5.0 https://github.com/netbox-community/netbox.git /tmp/netbox
          pip install --upgrade pip
          pip install -r /tmp/netbox/requirements.txt

      - name: Configure NetBox
        run: |
          cp .devcontainer/configuration/configuration.py /tmp/netbox/netbox/netbox/

          cat >> /tmp/netbox/netbox/netbox/configuration.py << 'EOF_PLUGINS'

          PLUGINS.append("netbox_rir_manager")
          PLUGINS_CONFIG["netbox_rir_manager"] = {}
          EOF_PLUGINS

          cat >> /tmp/netbox/netbox/netbox/configuration.py << EOF

          DATABASE = {
              'NAME': 'netbox',
              'USER': 'netbox',
              'PASSWORD': 'J5brHrAXFLQSif0K',
              'HOST': 'localhost',
              'PORT': '5432',
          }

          REDIS = {
              'tasks': {
                  'HOST': 'localhost',
                  'PORT': 6379,
                  'PASSWORD': '',
                  'DATABASE': 0,
                  'SSL': False,
              },
              'caching': {
                  'HOST': 'localhost',
                  'PORT': 6379,
                  'PASSWORD': '',
                  'DATABASE': 1,
                  'SSL': False,
              }
          }
          EOF

      - name: Install plugin
        run: |
          pip install -e ".[dev]"

      - name: Run migrations
        env:
          PYTHONPATH: /tmp/netbox/netbox
          DJANGO_SETTINGS_MODULE: netbox.settings
          NETBOX_CONFIGURATION: netbox.configuration
          SECRET_KEY: "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
        run: |
          cd /tmp/netbox/netbox
          python manage.py migrate --noinput

      - name: Run linting
        run: |
          ruff check netbox_rir_manager/ tests/
          ruff format --check netbox_rir_manager/ tests/

      - name: Run tests with coverage
        env:
          PYTHONPATH: /tmp/netbox/netbox
          DJANGO_SETTINGS_MODULE: netbox.settings
          NETBOX_CONFIGURATION: netbox.configuration
          SECRET_KEY: "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
        run: |
          pytest tests/ -v --tb=short --cov=netbox_rir_manager --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: false
          verbose: true
        env:
          CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}

      - name: Check migrations
        env:
          PYTHONPATH: /tmp/netbox/netbox
          DJANGO_SETTINGS_MODULE: netbox.settings
          NETBOX_CONFIGURATION: netbox.configuration
          SECRET_KEY: "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
        run: |
          cd /tmp/netbox/netbox
          python manage.py makemigrations --check --dry-run

      - name: Django system check
        env:
          PYTHONPATH: /tmp/netbox/netbox
          DJANGO_SETTINGS_MODULE: netbox.settings
          NETBOX_CONFIGURATION: netbox.configuration
          SECRET_KEY: "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
        run: |
          cd /tmp/netbox/netbox
          python manage.py check
```

**Step 2: Create publish workflow**

Create `.github/workflows/publish.yml` (same pattern as netbox-notices):

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  build:
    name: Build distribution
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install build dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build

      - name: Build package
        run: python -m build

      - name: Store distribution packages
        uses: actions/upload-artifact@v4
        with:
          name: python-package-distributions
          path: dist/

  publish-to-pypi:
    name: Publish to PyPI
    needs: [build]
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/netbox-rir-manager
    permissions:
      id-token: write

    steps:
      - name: Download distributions
        uses: actions/download-artifact@v4
        with:
          name: python-package-distributions
          path: dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

**Step 3: Commit**

```bash
git add .github/
git commit -m "feat: add CI and publish GitHub Actions workflows"
```

---

## Task 20: View Tests -- COMPLETED

**Files:**
- Create: `tests/test_views.py`

**Step 1: Write view tests**

Create `tests/test_views.py`:

```python
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestRIRAccountViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:riraccount_list")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_detail_view(self, admin_client, rir_account):
        url = reverse("plugins:netbox_rir_manager:riraccount", args=[rir_account.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_add_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:riraccount_add")
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestRIROrganizationViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:rirorganization_list")
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestRIRContactViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:rircontact_list")
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestRIRNetworkViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:rirnetwork_list")
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestRIRSyncLogViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:rirsynclog_list")
        response = admin_client.get(url)
        assert response.status_code == 200
```

Note: The `admin_client` fixture needs to return a Django test client (not DRF APIClient) for view tests. Update `conftest.py` to add:

```python
@pytest.fixture
def admin_client(db):
    from django.contrib.auth.models import User
    from django.test import Client

    user = User.objects.create_superuser("admin", "admin@example.com", "password")
    client = Client()
    client.force_login(user)
    return client
```

**Step 2: Run tests**

```bash
pytest tests/test_views.py -v
```

**Step 3: Commit**

```bash
git add tests/test_views.py
git commit -m "feat: add view tests"
```

---

## Task 21: Linting and Final Cleanup -- COMPLETED

**Step 1: Run ruff on the entire project**

```bash
ruff check netbox_rir_manager/ tests/ --fix
ruff format netbox_rir_manager/ tests/
```

**Step 2: Fix any issues**

Address any linting errors or formatting issues.

**Step 3: Run the full test suite**

```bash
pytest tests/ -v --cov=netbox_rir_manager --cov-report=term-missing
```

**Step 4: Run Django checks**

```bash
cd /tmp/netbox/netbox  # or devcontainer path
python manage.py check
python manage.py makemigrations --check --dry-run
```

**Step 5: Commit**

```bash
git add -A
git commit -m "chore: linting and cleanup pass"
```

---

## Summary of File Structure (current, after phase 2)

```
netbox-rir-manager/
├── .devcontainer/
│   ├── devcontainer.json
│   ├── docker-compose.yml
│   ├── Dockerfile-plugin_dev
│   ├── entrypoint-dev.sh
│   ├── requirements-dev.txt
│   ├── configuration/
│   │   ├── configuration.py
│   │   └── plugins.py
│   └── env/
│       ├── netbox.env
│       ├── postgres.env
│       └── redis.env
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── publish.yml
├── docs/
│   └── plans/
│       ├── 2026-02-04-netbox-rir-manager.md    (this plan)
│       └── 2026-02-05-sync-autolink-redesign.md (phase 2 plan)
├── netbox_rir_manager/
│   ├── __init__.py              (PluginConfig with ready() for signals)
│   ├── choices.py               (ChoiceSets)
│   ├── constants.py             (constants)
│   ├── filtersets.py            (FilterSets for all 6 models)
│   ├── forms.py                 (Forms + FilterForms for all 6 models)
│   ├── jobs.py                  (sync logic + SyncRIRConfigJob JobRunner)
│   ├── navigation.py            (PluginMenu)
│   ├── search.py                (SearchIndexes)
│   ├── signals.py               (auto-link RIRNetwork to Aggregate/Prefix)
│   ├── tables.py                (NetBoxTables for all 6 models)
│   ├── template_content.py      (PluginTemplateExtensions)
│   ├── urls.py                  (URL patterns incl. sync trigger)
│   ├── views.py                 (generic views + RIRConfigSyncView)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── backends/
│   │   ├── __init__.py          (registry)
│   │   ├── base.py              (RIRBackend ABC)
│   │   └── arin.py              (ARINBackend with find_net, poc_links)
│   ├── migrations/
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   ├── 0002_rename_riraccount_to_rirconfig.py
│   │   └── 0003_add_riruserkey_and_contact_link.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── accounts.py          (RIRConfig, renamed from RIRAccount)
│   │   ├── credentials.py       (RIRUserKey)
│   │   ├── resources.py         (RIROrganization, RIRContact, RIRNetwork)
│   │   └── sync.py              (RIRSyncLog)
│   └── templates/
│       └── netbox_rir_manager/
│           ├── rirconfig.html
│           ├── rirorganization.html
│           ├── rircontact.html
│           ├── rirnetwork.html
│           ├── rirsynclog.html
│           ├── riruserkey.html
│           └── inc/
│               └── rir_network_panel.html
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_filtersets.py
│   ├── test_jobs.py
│   ├── test_models.py
│   ├── test_signals.py
│   ├── test_views.py
│   └── test_backends/
│       ├── __init__.py
│       ├── test_arin.py
│       └── test_base.py
├── .gitignore
├── .pre-commit-config.yaml
├── LICENSE
└── pyproject.toml
```

---

## Deferred for Future Iterations

These items are intentionally deferred:

1. **Write Operations** (create/update POCs, submit reassignments) - requires careful ARIN OTE testing
2. **Sync Dashboard View** - custom view with progress feedback
3. **Scheduled/Periodic Sync** - `@system_job` decorator for automated recurring sync
4. **Discrepancy Reports** - requires both local and RIR data to compare
5. **API key encryption** - django-encrypted-model-fields integration
6. **Rate limiting / retry logic** - add when hitting real API
7. **Additional RIR backends** (RIPE, APNIC, etc.) - backend interface is ready for them

Items completed in phase 2 (originally deferred):
- ~~Scheduled Background Sync~~ → JobRunner integration added (`SyncRIRConfigJob`)
- ~~Auto-linking networks to Aggregates/Prefixes~~ → `post_save` signal handler implemented
