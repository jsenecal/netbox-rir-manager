# Sync, Auto-Link, and Model Redesign Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the data model (RIRAccount → RIRConfig, per-user API keys), complete sync operations (orgs, POCs, networks), add auto-linking of RIR networks to NetBox IPAM objects, and integrate with NetBox's JobRunner for background sync.

**Key Design Decisions:**
- API keys are per-user, not per-org. `RIRUserKey` links a NetBox User to an API key scoped to an `RIRConfig`.
- `RIRContact` links to `tenancy.Contact` (not User) for identity mapping.
- Network discovery works by matching existing NetBox Aggregates/Prefixes (where `rir` matches) against ARIN via pyregrws `find_net()`.
- Sync runs as a background job via NetBox's `JobRunner` framework.
- Auto-linking is a post_save signal on `RIRNetwork`, controlled by the `auto_link_networks` plugin setting.

---

## Task 1: Rename RIRAccount → RIRConfig

**Files:**
- Modify: `netbox_rir_manager/models/accounts.py`
- Modify: `netbox_rir_manager/models/__init__.py`
- Modify: `netbox_rir_manager/models/resources.py`
- Modify: `netbox_rir_manager/models/sync.py`
- Modify: `netbox_rir_manager/tables.py`
- Modify: `netbox_rir_manager/filtersets.py`
- Modify: `netbox_rir_manager/forms.py`
- Modify: `netbox_rir_manager/views.py`
- Modify: `netbox_rir_manager/urls.py`
- Modify: `netbox_rir_manager/navigation.py`
- Modify: `netbox_rir_manager/search.py`
- Modify: `netbox_rir_manager/api/serializers.py`
- Modify: `netbox_rir_manager/api/views.py`
- Modify: `netbox_rir_manager/api/urls.py`
- Modify: `netbox_rir_manager/template_content.py`
- Modify: `netbox_rir_manager/jobs.py`
- Modify: All templates referencing RIRAccount
- Modify: All test files
- New migration

**Step 1: Rename the model class**

In `netbox_rir_manager/models/accounts.py`:
- Rename `RIRAccount` → `RIRConfig`
- Remove the `api_key` field
- Rename FK `related_name` values from `rir_accounts` to `rir_configs`
- Update `get_absolute_url` to use `rirconfig`
- Update `Meta.constraints` name

```python
class RIRConfig(NetBoxModel):
    """Organization-level configuration for RIR API access."""

    rir = models.ForeignKey(RIR, on_delete=models.CASCADE, related_name="rir_configs")
    name = models.CharField(max_length=100)
    api_url = models.URLField(blank=True, default="")
    org_handle = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["rir", "name"]
        constraints = [
            models.UniqueConstraint(fields=["rir", "name"], name="unique_rir_config_name"),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirconfig", args=[self.pk])
```

**Step 2: Update all FK references**

In `models/resources.py` and `models/sync.py`:
- Rename `account` field → `rir_config` on RIROrganization, RIRContact, RIRNetwork, RIRSyncLog
- Update `related_name` values accordingly
- Update FK reference string from `"netbox_rir_manager.RIRAccount"` → `"netbox_rir_manager.RIRConfig"`

**Step 3: Update `models/__init__.py`**

```python
from netbox_rir_manager.models.accounts import RIRConfig
from netbox_rir_manager.models.resources import RIRContact, RIRNetwork, RIROrganization
from netbox_rir_manager.models.sync import RIRSyncLog

__all__ = [
    "RIRConfig",
    "RIRContact",
    "RIRNetwork",
    "RIROrganization",
    "RIRSyncLog",
]
```

**Step 4: Update all downstream references**

Rename throughout (search-and-replace where safe, manual where context matters):
- `tables.py`: `RIRAccountTable` → `RIRConfigTable`, field references `account` → `rir_config`
- `filtersets.py`: `RIRAccountFilterSet` → `RIRConfigFilterSet`, filter fields
- `forms.py`: `RIRAccountForm` → `RIRConfigForm`, `RIRAccountFilterForm` → `RIRConfigFilterForm`, remove `api_key` widget
- `views.py`: All `RIRAccount*View` → `RIRConfig*View`
- `urls.py`: All `riraccount` URL names → `rirconfig`
- `navigation.py`: Update link names and permissions
- `search.py`: `RIRAccountIndex` → `RIRConfigIndex`
- `api/serializers.py`: `RIRAccountSerializer` → `RIRConfigSerializer`, remove `api_key` field
- `api/views.py`: `RIRAccountViewSet` → `RIRConfigViewSet`
- `api/urls.py`: Update router registration
- `template_content.py`: Update if referencing account
- `jobs.py`: Update references
- Templates: Rename `riraccount.html` → `rirconfig.html`, update content

**Step 5: Update all tests**

- `conftest.py`: Rename `rir_account` fixture → `rir_config`, update model references
- `test_models.py`: `TestRIRAccount` → `TestRIRConfig`, all references
- `test_views.py`: Update URL names and fixture references
- `test_api.py`: Update URL names, fixture references, class names
- `test_filtersets.py`: Update class and fixture references
- `test_jobs.py`: Update fixture references

**Step 6: Generate migration**

```bash
python manage.py makemigrations netbox_rir_manager
```

Django should detect the rename. If not, manually create a migration with `RenameModel` and `RenameField` operations. The migration must:
- Rename model `RIRAccount` → `RIRConfig`
- Remove `api_key` column
- Rename FK fields `account` → `rir_config` on all resource models
- Rename constraint `unique_rir_account_name` → `unique_rir_config_name`

**Step 7: Run tests**

```bash
pytest tests/ -v
```

**Step 8: Commit**

```bash
git add -A
git commit -m "refactor: rename RIRAccount to RIRConfig, remove api_key"
```

---

## Task 2: Add RIRUserKey Model

**Files:**
- Create: `netbox_rir_manager/models/credentials.py`
- Modify: `netbox_rir_manager/models/__init__.py`
- Modify: `netbox_rir_manager/tables.py`
- Modify: `netbox_rir_manager/filtersets.py`
- Modify: `netbox_rir_manager/forms.py`
- Modify: `netbox_rir_manager/views.py`
- Modify: `netbox_rir_manager/urls.py`
- Modify: `netbox_rir_manager/navigation.py`
- Modify: `netbox_rir_manager/api/serializers.py`
- Modify: `netbox_rir_manager/api/views.py`
- Modify: `netbox_rir_manager/api/urls.py`
- Create: `netbox_rir_manager/templates/netbox_rir_manager/riruserkey.html`
- Modify: `tests/conftest.py`
- Modify: `tests/test_models.py`
- New migration

**Step 1: Write failing test**

Add to `tests/test_models.py`:

```python
@pytest.mark.django_db
class TestRIRUserKey:
    def test_create_user_key(self, rir_config, admin_user):
        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(
            user=admin_user,
            rir_config=rir_config,
            api_key="user-api-key-123",
        )
        assert key.pk is not None
        assert str(key) == f"admin - {rir_config.name}"

    def test_user_key_unique_per_config(self, rir_config, admin_user):
        from django.db import IntegrityError
        from netbox_rir_manager.models import RIRUserKey

        RIRUserKey.objects.create(user=admin_user, rir_config=rir_config, api_key="key1")
        with pytest.raises(IntegrityError):
            RIRUserKey.objects.create(user=admin_user, rir_config=rir_config, api_key="key2")
```

**Step 2: Write model**

Create `netbox_rir_manager/models/credentials.py`:

```python
from django.conf import settings
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel


class RIRUserKey(NetBoxModel):
    """Per-user API key for RIR access, scoped to an RIRConfig."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rir_user_keys",
    )
    rir_config = models.ForeignKey(
        "netbox_rir_manager.RIRConfig",
        on_delete=models.CASCADE,
        related_name="user_keys",
    )
    api_key = models.CharField(max_length=255)

    class Meta:
        ordering = ["user", "rir_config"]
        constraints = [
            models.UniqueConstraint(fields=["user", "rir_config"], name="unique_user_rir_config"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.rir_config.name}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:riruserkey", args=[self.pk])
```

**Step 3: Update `models/__init__.py`**

Add `RIRUserKey` to imports and `__all__`.

**Step 4: Add table, filterset, form, views, URLs, navigation, API, template**

Follow the same patterns as other models:
- Table: `RIRUserKeyTable` with columns user, rir_config
- FilterSet: filter by user, rir_config
- Form: `RIRUserKeyForm` with api_key as PasswordInput widget
- Views: List, Detail, Edit, Delete
- URLs: `user-keys/` prefix
- Navigation: Add under "Accounts" group
- API serializer: `RIRUserKeySerializer` with `api_key` as write-only
- API viewset and URL registration
- Detail template: `riruserkey.html`

**Step 5: Generate migration, run tests, commit**

```bash
python manage.py makemigrations netbox_rir_manager
pytest tests/ -v
git add -A
git commit -m "feat: add RIRUserKey model for per-user API credentials"
```

---

## Task 3: Add Contact Link to RIRContact

**Files:**
- Modify: `netbox_rir_manager/models/resources.py`
- Modify: `netbox_rir_manager/tables.py`
- Modify: `netbox_rir_manager/forms.py`
- Modify: `netbox_rir_manager/api/serializers.py`
- Modify: `netbox_rir_manager/templates/netbox_rir_manager/rircontact.html`
- Modify: `tests/test_models.py`
- New migration

**Step 1: Write failing test**

```python
@pytest.mark.django_db
class TestRIRContactLink:
    def test_link_to_netbox_contact(self, rir_contact):
        from tenancy.models import Contact

        nb_contact = Contact.objects.create(name="John Doe")
        rir_contact.contact = nb_contact
        rir_contact.save()
        rir_contact.refresh_from_db()
        assert rir_contact.contact == nb_contact
```

**Step 2: Add field to RIRContact**

In `netbox_rir_manager/models/resources.py`, add to `RIRContact`:

```python
contact = models.ForeignKey(
    "tenancy.Contact",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="rir_contacts",
)
```

**Step 3: Update table, form, serializer, template**

- Table: Add `contact` column with linkify
- Form: Add `contact` as DynamicModelChoiceField
- Serializer: Add `contact` to fields
- Template: Add row showing linked contact

**Step 4: Generate migration, run tests, commit**

```bash
python manage.py makemigrations netbox_rir_manager
pytest tests/ -v
git add -A
git commit -m "feat: add optional tenancy.Contact link to RIRContact"
```

---

## Task 4: Complete Sync Operations (POCs and Networks)

**Files:**
- Modify: `netbox_rir_manager/jobs.py`
- Modify: `netbox_rir_manager/backends/arin.py`
- Modify: `tests/test_jobs.py`

**Step 1: Write failing tests**

Add to `tests/test_jobs.py`:

```python
@patch("netbox_rir_manager.jobs.ARINBackend")
def test_sync_contacts_from_org(self, mock_backend_class, rir_config):
    from netbox_rir_manager.jobs import sync_rir_config
    from netbox_rir_manager.models import RIRContact, RIROrganization

    mock_backend = MagicMock()
    mock_backend.get_organization.return_value = {
        "handle": "TESTORG-ARIN",
        "name": "Test Org",
        "street_address": "",
        "city": "Anytown",
        "state_province": "VA",
        "postal_code": "12345",
        "country": "US",
        "poc_links": [{"handle": "JD123-ARIN", "function": "AD"}],
        "raw_data": {},
    }
    mock_backend.get_poc.return_value = {
        "handle": "JD123-ARIN",
        "contact_type": "PERSON",
        "first_name": "John",
        "last_name": "Doe",
        "company_name": "Test Org",
        "city": "Anytown",
        "postal_code": "12345",
        "country": "US",
        "raw_data": {},
    }
    mock_backend_class.return_value = mock_backend

    sync_rir_config(rir_config, api_key="test-key", resource_types=["organizations", "contacts"])

    assert RIROrganization.objects.filter(handle="TESTORG-ARIN").exists()
    assert RIRContact.objects.filter(handle="JD123-ARIN").exists()


@patch("netbox_rir_manager.jobs.ARINBackend")
def test_sync_networks_from_ipam(self, mock_backend_class, rir_config, rir):
    from ipam.models import Aggregate
    from netbox_rir_manager.jobs import sync_rir_config
    from netbox_rir_manager.models import RIRNetwork

    Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)

    mock_backend = MagicMock()
    mock_backend.get_organization.return_value = {
        "handle": "TESTORG-ARIN",
        "name": "Test Org",
        "street_address": "", "city": "", "state_province": "",
        "postal_code": "", "country": "", "poc_links": [], "raw_data": {},
    }
    mock_net = {
        "handle": "NET-192-0-2-0-1",
        "net_name": "EXAMPLE-NET",
        "version": 4,
        "org_handle": "TESTORG-ARIN",
        "parent_net_handle": "",
        "net_blocks": [{"start_address": "192.0.2.0", "end_address": "192.0.2.255", "cidr_length": 24, "type": "DS"}],
        "raw_data": {},
    }
    mock_backend.find_net.return_value = mock_net
    mock_backend_class.return_value = mock_backend

    sync_rir_config(rir_config, api_key="test-key")

    net = RIRNetwork.objects.get(handle="NET-192-0-2-0-1")
    assert net.net_name == "EXAMPLE-NET"
```

**Step 2: Update `_org_to_dict` in ARIN backend**

Add `poc_links` extraction to `_org_to_dict()` in `backends/arin.py`:

```python
def _org_to_dict(self, org) -> dict[str, Any]:
    # ... existing code ...
    poc_links = []
    if hasattr(org, "poc_links") and org.poc_links:
        for link in org.poc_links:
            poc_links.append({
                "handle": link.handle,
                "function": getattr(link, "function", ""),
            })
    return {
        # ... existing fields ...
        "poc_links": poc_links,
    }
```

Add `find_net` method to `ARINBackend`:

```python
def find_net(self, start_address: str, end_address: str) -> dict[str, Any] | None:
    result = self.api.net.find_net(start_address, end_address)
    if isinstance(result, Error):
        return None
    return self._net_to_dict(result)
```

**Step 3: Rewrite `jobs.py`**

Rename `sync_account` → `sync_rir_config`. Update signature to accept `api_key` parameter instead of relying on account credentials.

Add `_sync_contacts(backend, rir_config, poc_links)`:
- For each handle in `poc_links`, call `backend.get_poc(handle)`
- `update_or_create` on `RIRContact` by handle
- Create `RIRSyncLog` entries

Add `_sync_networks(backend, rir_config)`:
- Query `Aggregate.objects.filter(rir=rir_config.rir)` and `Prefix.objects.filter(rir=rir_config.rir)` (Prefix only if it has an rir field — check NetBox model)
- For each, compute start/end addresses and call `backend.find_net()`
- If found, `update_or_create` on `RIRNetwork` by handle, setting `aggregate` or `prefix` FK
- Create `RIRSyncLog` entries

Update `sync_rir_config()` to call all three sync functions in order: org → contacts → networks.

**Step 4: Run tests, commit**

```bash
pytest tests/ -v
git add -A
git commit -m "feat: complete sync operations for POCs and networks"
```

---

## Task 5: Auto-Link Signal Handler

**Files:**
- Modify: `netbox_rir_manager/signals.py`
- Modify: `netbox_rir_manager/__init__.py`
- Create: `tests/test_signals.py`

**Step 1: Write failing test**

Create `tests/test_signals.py`:

```python
import pytest


@pytest.mark.django_db
class TestAutoLinkSignal:
    def test_auto_links_aggregate_on_save(self, rir_config, rir):
        from ipam.models import Aggregate
        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-192-0-2-0-1",
            net_name="EXAMPLE-NET",
            raw_data={
                "net_blocks": [
                    {"start_address": "192.0.2.0", "cidr_length": 24, "type": "DS"}
                ]
            },
        )
        net.refresh_from_db()
        assert net.aggregate == agg

    def test_auto_link_does_not_overwrite_existing(self, rir_config, rir):
        from ipam.models import Aggregate
        from netbox_rir_manager.models import RIRNetwork

        agg1 = Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
        agg2 = Aggregate.objects.create(prefix="10.0.0.0/8", rir=rir)
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-192-0-2-0-1",
            net_name="EXAMPLE-NET",
            aggregate=agg2,  # manually set to different aggregate
            raw_data={
                "net_blocks": [
                    {"start_address": "192.0.2.0", "cidr_length": 24, "type": "DS"}
                ]
            },
        )
        net.refresh_from_db()
        assert net.aggregate == agg2  # should NOT be overwritten

    def test_auto_link_disabled_by_setting(self, rir_config, rir, settings):
        from ipam.models import Aggregate
        from netbox_rir_manager.models import RIRNetwork

        settings.PLUGINS_CONFIG["netbox_rir_manager"]["auto_link_networks"] = False
        agg = Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-DISABLED-1",
            net_name="DISABLED-NET",
            raw_data={
                "net_blocks": [
                    {"start_address": "192.0.2.0", "cidr_length": 24, "type": "DS"}
                ]
            },
        )
        net.refresh_from_db()
        assert net.aggregate is None
```

**Step 2: Implement signal handler**

In `netbox_rir_manager/signals.py`:

```python
import ipaddress
import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="netbox_rir_manager.RIRNetwork")
def auto_link_network(sender, instance, created, raw=False, **kwargs):
    """Auto-link RIRNetwork to matching Aggregate/Prefix based on net_blocks."""
    if raw:
        return

    plugin_config = settings.PLUGINS_CONFIG.get("netbox_rir_manager", {})
    if not plugin_config.get("auto_link_networks", True):
        return

    # Don't overwrite existing links
    if instance.aggregate is not None or instance.prefix is not None:
        return

    net_blocks = (instance.raw_data or {}).get("net_blocks", [])
    if not net_blocks:
        return

    from ipam.models import Aggregate, Prefix

    for block in net_blocks:
        start = block.get("start_address")
        cidr = block.get("cidr_length")
        if not start or cidr is None:
            continue

        try:
            network = ipaddress.ip_network(f"{start}/{cidr}", strict=False)
            prefix_str = str(network)
        except ValueError:
            continue

        # Try matching Aggregate first
        agg = Aggregate.objects.filter(prefix=prefix_str).first()
        if agg:
            instance.aggregate = agg
            instance.save(update_fields=["aggregate"])
            return

        # Then try Prefix
        pfx = Prefix.objects.filter(prefix=prefix_str).first()
        if pfx:
            instance.prefix = pfx
            instance.save(update_fields=["prefix"])
            return
```

**Step 3: Add `ready()` method to plugin config**

In `netbox_rir_manager/__init__.py`:

```python
class NetBoxRIRManagerConfig(PluginConfig):
    # ... existing config ...

    def ready(self):
        super().ready()
        from . import signals  # noqa: F401
```

**Step 4: Run tests, commit**

```bash
pytest tests/ -v
git add -A
git commit -m "feat: add auto-link signal for RIRNetwork to Aggregate/Prefix"
```

---

## Task 6: Background Job Integration (JobRunner)

**Files:**
- Modify: `netbox_rir_manager/jobs.py`
- Modify: `netbox_rir_manager/views.py`
- Modify: `netbox_rir_manager/urls.py`
- Modify: `netbox_rir_manager/templates/netbox_rir_manager/rirconfig.html`
- Modify: `tests/test_jobs.py`

**Step 1: Create JobRunner class**

In `netbox_rir_manager/jobs.py`, add:

```python
from netbox.jobs import JobRunner


class SyncRIRConfigJob(JobRunner):
    """Background job for syncing RIR data."""

    class Meta:
        name = "RIR Sync"

    def run(self, *args, **kwargs):
        from netbox_rir_manager.models import RIRConfig, RIRUserKey

        rir_config = RIRConfig.objects.get(pk=self.job.object_id)
        user_id = kwargs.get("user_id") or (args[0] if args else None)

        user_key = RIRUserKey.objects.get(user_id=user_id, rir_config=rir_config)

        self.logger.info(f"Starting sync for {rir_config.name}")
        logs = sync_rir_config(rir_config, api_key=user_key.api_key)
        self.logger.info(f"Sync complete: {len(logs)} operations")
```

**Step 2: Add sync trigger view**

In `netbox_rir_manager/views.py`, add a view to trigger sync:

```python
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin


class RIRConfigSyncView(LoginRequiredMixin, View):
    """Trigger a background sync job for an RIRConfig."""

    def post(self, request, pk):
        from netbox_rir_manager.jobs import SyncRIRConfigJob
        from netbox_rir_manager.models import RIRConfig, RIRUserKey

        rir_config = get_object_or_404(RIRConfig, pk=pk)

        # Check user has a key for this config
        if not RIRUserKey.objects.filter(user=request.user, rir_config=rir_config).exists():
            messages.error(request, "You don't have an API key configured for this RIR config.")
            return redirect(rir_config.get_absolute_url())

        SyncRIRConfigJob.enqueue(
            instance=rir_config,
            user=request.user,
            user_id=request.user.pk,
        )
        messages.success(request, f"Sync job queued for {rir_config.name}.")
        return redirect(rir_config.get_absolute_url())
```

**Step 3: Add URL**

In `netbox_rir_manager/urls.py`:

```python
path("configs/<int:pk>/sync/", views.RIRConfigSyncView.as_view(), name="rirconfig_sync"),
```

**Step 4: Update RIRConfig detail template**

Add "Sync Now" button (only shown if user has a key) and recent sync logs panel to `rirconfig.html`.

**Step 5: Run tests, commit**

```bash
pytest tests/ -v
git add -A
git commit -m "feat: add JobRunner integration and sync trigger view"
```

---

## Task 7: Update CI and Final Cleanup

**Files:**
- Modify: `.github/workflows/ci.yml` (if needed)
- All files: linting pass

**Step 1: Run ruff**

```bash
ruff check netbox_rir_manager/ tests/ --fix
ruff format netbox_rir_manager/ tests/
```

**Step 2: Run full test suite**

```bash
pytest tests/ -v --cov=netbox_rir_manager --cov-report=term-missing
```

**Step 3: Run Django checks**

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: final linting and cleanup"
```

---

## Summary of Changes

| Component | Change |
|---|---|
| `RIRAccount` → `RIRConfig` | Rename model, remove `api_key`, update all references |
| `RIRUserKey` | New model: user + rir_config + api_key (unique together) |
| `RIRContact.contact` | New optional FK to `tenancy.Contact` |
| `jobs.py` | Complete sync: orgs → POCs → networks. Wrap in `SyncRIRConfigJob` (JobRunner) |
| `backends/arin.py` | Add `find_net()`, add `poc_links` to org dict |
| `signals.py` | Auto-link `RIRNetwork` to Aggregate/Prefix on post_save |
| `__init__.py` | Add `ready()` to register signals |
| Views/templates | "Sync Now" button on RIRConfig detail, sync log panel |
| Network discovery | Match NetBox IPAM Aggregates (rir=matching) via pyregrws `find_net()` |

## Deferred (still future)

- Scheduled/periodic sync (`@system_job` decorator)
- Write operations (create/update POCs, reassignments)
- Discrepancy reports
- API key encryption
- Rate limiting / retry logic
- Additional RIR backends
