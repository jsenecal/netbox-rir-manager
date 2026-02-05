# Core Reliability: Encryption, Scheduled Sync, and Retry

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the plugin production-ready by encrypting API keys at rest, adding scheduled background sync, tracking which credentials synced each object, and adding retry logic with exponential backoff for ARIN API calls.

**Architecture:** API keys are encrypted using Fernet symmetric encryption via a custom `EncryptedCharField`. Scheduled sync uses NetBox's `@system_job` decorator with daily interval. Each synced object tracks its `synced_by` key so the scheduler can group API calls by credential and reuse backend instances. Retry logic uses the `tenacity` library on all ARIN backend methods.

**Tech Stack:** Python 3.12+, cryptography (Fernet + HKDF), tenacity, NetBox `@system_job`

**Key Design Decisions:**
- `EncryptedCharField` handles encrypt/decrypt transparently — no model `save()` overrides needed.
- HKDF-SHA256 derives the Fernet key from the plugin's `encryption_key` setting (defaults to `SECRET_KEY`). Faster than PBKDF2 since SECRET_KEY already has high entropy.
- `$FERNET$` prefix on ciphertext allows the field to detect plaintext values (for migration) and avoid double-encryption.
- `synced_by` FK on resource models is internal-only — excluded from forms, serializers, and templates.
- Scheduled sync groups objects by `synced_by` key to reuse `ARINBackend` instances (one per credential).
- `tenacity` is added as a project dependency and used to wrap ARIN backend API calls with exponential backoff.

---

## Task 1: Add EncryptedCharField

**Files:**
- Create: `netbox_rir_manager/fields.py`
- Create: `tests/test_fields.py`

**Step 1: Write failing tests**

Create `tests/test_fields.py`:

```python
import pytest


@pytest.mark.django_db
class TestEncryptedCharField:
    def test_encrypts_on_save_and_decrypts_on_read(self, rir_config, admin_user):
        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(
            user=admin_user, rir_config=rir_config, api_key="my-secret-key"
        )
        key.refresh_from_db()
        # Python attribute returns plaintext
        assert key.api_key == "my-secret-key"

    def test_raw_db_value_is_encrypted(self, rir_config, admin_user):
        from django.db import connection

        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(
            user=admin_user, rir_config=rir_config, api_key="my-secret-key"
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT api_key FROM netbox_rir_manager_riruserkey WHERE id = %s",
                [key.pk],
            )
            raw_value = cursor.fetchone()[0]
        assert raw_value.startswith("$FERNET$")
        assert "my-secret-key" not in raw_value

    def test_handles_empty_string(self, rir_config, admin_user):
        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(
            user=admin_user, rir_config=rir_config, api_key=""
        )
        key.refresh_from_db()
        assert key.api_key == ""

    def test_handles_none(self, rir_config, admin_user):
        """None values pass through without encryption."""
        from netbox_rir_manager.fields import EncryptedCharField

        field = EncryptedCharField(max_length=512)
        assert field.get_prep_value(None) is None
        assert field.from_db_value(None, None, None) is None

    def test_idempotent_encryption(self, rir_config, admin_user):
        """Saving twice doesn't double-encrypt."""
        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(
            user=admin_user, rir_config=rir_config, api_key="idempotent-key"
        )
        key.save()  # second save
        key.refresh_from_db()
        assert key.api_key == "idempotent-key"

    def test_plaintext_migrated_on_read(self, rir_config, admin_user):
        """A plaintext value in the DB (pre-migration) decrypts correctly."""
        from django.db import connection

        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(
            user=admin_user, rir_config=rir_config, api_key="will-be-forced-plain"
        )
        # Simulate a pre-migration plaintext value
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE netbox_rir_manager_riruserkey SET api_key = %s WHERE id = %s",
                ["old-plain-key", key.pk],
            )
        key.refresh_from_db()
        assert key.api_key == "old-plain-key"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_fields.py -v`
Expected: FAIL (fields module doesn't exist yet)

**Step 3: Implement EncryptedCharField**

Create `netbox_rir_manager/fields.py`:

```python
from __future__ import annotations

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from django.db import models

_FERNET_PREFIX = "$FERNET$"
_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        plugin_config = getattr(settings, "PLUGINS_CONFIG", {}).get("netbox_rir_manager", {})
        secret = plugin_config.get("encryption_key") or settings.SECRET_KEY
        derived = HKDF(
            algorithm=SHA256(),
            length=32,
            salt=b"netbox-rir-manager",
            info=b"api-key-encryption",
        ).derive(secret.encode())
        _fernet_instance = Fernet(base64.urlsafe_b64encode(derived))
    return _fernet_instance


def _encrypt(value: str) -> str:
    if not value:
        return value
    if value.startswith(_FERNET_PREFIX):
        return value  # already encrypted
    token = _get_fernet().encrypt(value.encode())
    return f"{_FERNET_PREFIX}{token.decode()}"


def _decrypt(value: str) -> str:
    if not value:
        return value
    if not value.startswith(_FERNET_PREFIX):
        return value  # plaintext (pre-migration)
    token = value[len(_FERNET_PREFIX) :]
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return value


class EncryptedCharField(models.CharField):
    """CharField that encrypts values at rest using Fernet."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return value
        return _encrypt(value)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return _decrypt(value)
```

**Step 4: Update RIRUserKey model to use EncryptedCharField**

In `netbox_rir_manager/models/credentials.py`, change:

```python
api_key = models.CharField(max_length=255)
```

to:

```python
from netbox_rir_manager.fields import EncryptedCharField

api_key = EncryptedCharField(max_length=512)
```

**Step 5: Generate migration**

```bash
python /opt/netbox/netbox/manage.py makemigrations netbox_rir_manager
```

This should produce a migration that alters `api_key` from CharField(max_length=255) to EncryptedCharField(max_length=512).

**Step 6: Run tests to verify they pass**

```bash
pytest tests/test_fields.py -v
pytest tests/ -v
```

Expected: ALL PASS. The existing tests that create RIRUserKey objects should still work since EncryptedCharField is transparent.

**Step 7: Commit**

```bash
git add netbox_rir_manager/fields.py netbox_rir_manager/models/credentials.py netbox_rir_manager/migrations/ tests/test_fields.py
git commit -m "feat: add EncryptedCharField for API key encryption at rest"
```

---

## Task 2: Add `synced_by` FK to Resource Models

**Files:**
- Modify: `netbox_rir_manager/models/resources.py`
- Modify: `netbox_rir_manager/jobs.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_jobs.py`
- New migration

**Step 1: Write failing tests**

Add to `tests/test_models.py`:

```python
@pytest.mark.django_db
class TestSyncedByTracking:
    def test_organization_synced_by(self, rir_config, rir_user_key):
        from netbox_rir_manager.models import RIROrganization

        org = RIROrganization.objects.create(
            rir_config=rir_config,
            handle="SYNCTEST-ARIN",
            name="Sync Test Org",
            synced_by=rir_user_key,
        )
        org.refresh_from_db()
        assert org.synced_by == rir_user_key

    def test_contact_synced_by(self, rir_config, rir_user_key):
        from netbox_rir_manager.models import RIRContact

        contact = RIRContact.objects.create(
            rir_config=rir_config,
            handle="SYNCPOC-ARIN",
            contact_type="PERSON",
            last_name="Test",
            synced_by=rir_user_key,
        )
        contact.refresh_from_db()
        assert contact.synced_by == rir_user_key

    def test_network_synced_by(self, rir_config, rir_user_key):
        from netbox_rir_manager.models import RIRNetwork

        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="SYNCNET-1",
            net_name="SYNC-NET",
            synced_by=rir_user_key,
        )
        net.refresh_from_db()
        assert net.synced_by == rir_user_key

    def test_synced_by_set_null_on_key_delete(self, rir_config, rir_user_key):
        from netbox_rir_manager.models import RIROrganization

        org = RIROrganization.objects.create(
            rir_config=rir_config,
            handle="NULLTEST-ARIN",
            name="Null Test Org",
            synced_by=rir_user_key,
        )
        rir_user_key.delete()
        org.refresh_from_db()
        assert org.synced_by is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models.py::TestSyncedByTracking -v`
Expected: FAIL (synced_by field doesn't exist)

**Step 3: Add synced_by FK to all three resource models**

In `netbox_rir_manager/models/resources.py`, add to `RIROrganization`, `RIRContact`, and `RIRNetwork`:

```python
synced_by = models.ForeignKey(
    "netbox_rir_manager.RIRUserKey",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="synced_%(class)ss",
    editable=False,
)
```

Place it after `last_synced` on each model. The `editable=False` ensures Django forms never include it.

**Step 4: Update sync functions to set synced_by**

In `netbox_rir_manager/jobs.py`:

Change `sync_rir_config` signature to accept an optional `user_key` parameter:

```python
def sync_rir_config(
    rir_config: RIRConfig,
    api_key: str,
    resource_types: list[str] | None = None,
    user_key: RIRUserKey | None = None,
) -> list[RIRSyncLog]:
```

Add `from netbox_rir_manager.models import RIRUserKey` to the TYPE_CHECKING imports.

Pass `user_key` through to `_sync_organization`, `_sync_contacts`, and `_sync_networks`. In each function, add `"synced_by": user_key` to the `defaults` dict of every `update_or_create` call.

Update `_sync_organization` signature:
```python
def _sync_organization(
    backend: ARINBackend, rir_config: RIRConfig, user_key: RIRUserKey | None = None
) -> tuple[list[RIRSyncLog], RIROrganization | None]:
```

Update `_sync_contacts` signature:
```python
def _sync_contacts(
    backend: ARINBackend, rir_config: RIRConfig, poc_links: list[dict], org: RIROrganization,
    user_key: RIRUserKey | None = None,
) -> list[RIRSyncLog]:
```

Update `_sync_networks` signature:
```python
def _sync_networks(
    backend: ARINBackend, rir_config: RIRConfig, user_key: RIRUserKey | None = None
) -> list[RIRSyncLog]:
```

Update `SyncRIRConfigJob.run()` to pass the `user_key` instance:
```python
logs = sync_rir_config(rir_config, api_key=user_key.api_key, user_key=user_key)
```

**Step 5: Generate migration**

```bash
python /opt/netbox/netbox/manage.py makemigrations netbox_rir_manager
```

**Step 6: Update sync job tests**

In `tests/test_jobs.py`, update existing sync tests to verify `synced_by` is set when a `user_key` is passed. Add one new test:

```python
@patch("netbox_rir_manager.jobs.ARINBackend")
def test_sync_sets_synced_by(self, mock_backend_class, rir_config, rir_user_key):
    from netbox_rir_manager.jobs import sync_rir_config
    from netbox_rir_manager.models import RIROrganization

    mock_backend = MagicMock()
    mock_backend.get_organization.return_value = {
        "handle": "SYNCBY-ARIN",
        "name": "Sync By Org",
        "street_address": "",
        "city": "",
        "state_province": "",
        "postal_code": "",
        "country": "",
        "poc_links": [],
        "raw_data": {},
    }
    mock_backend.find_net.return_value = None
    mock_backend_class.from_rir_config.return_value = mock_backend

    sync_rir_config(rir_config, api_key="test-key", user_key=rir_user_key)

    org = RIROrganization.objects.get(handle="SYNCBY-ARIN")
    assert org.synced_by == rir_user_key
```

**Step 7: Run tests**

```bash
pytest tests/ -v
```

Expected: ALL PASS

**Step 8: Commit**

```bash
git add netbox_rir_manager/models/resources.py netbox_rir_manager/jobs.py netbox_rir_manager/migrations/ tests/test_models.py tests/test_jobs.py
git commit -m "feat: add synced_by tracking on resource models"
```

---

## Task 3: Add tenacity Dependency and Retry Logic

**Files:**
- Modify: `pyproject.toml`
- Modify: `netbox_rir_manager/backends/arin.py`
- Modify: `netbox_rir_manager/__init__.py`
- Create: `tests/test_backends/test_retry.py`

**Step 1: Add tenacity dependency**

In `pyproject.toml`, add to `dependencies`:

```toml
dependencies = [
    "pyregrws>=0.2.0",
    "tenacity>=8.0",
]
```

Install it:

```bash
pip install tenacity
```

**Step 2: Write failing tests**

Create `tests/test_backends/test_retry.py`:

```python
from unittest.mock import MagicMock, patch

import pytest
from regrws.models import Error


@pytest.mark.django_db
class TestARINBackendRetry:
    def test_get_organization_retries_on_exception(self):
        from netbox_rir_manager.backends.arin import ARINBackend

        backend = ARINBackend(api_key="test")
        mock_org = MagicMock()
        mock_org.handle = "TEST-ARIN"
        mock_org.org_name = "Test"
        mock_org.street_address = None
        mock_org.poc_links = None
        mock_org.city = ""
        mock_org.iso3166_2 = ""
        mock_org.postal_code = ""
        mock_org.iso3166_1 = None

        # First two calls raise, third succeeds
        backend.api.org.from_handle = MagicMock(
            side_effect=[ConnectionError("timeout"), ConnectionError("timeout"), mock_org]
        )
        result = backend.get_organization("TEST-ARIN")
        assert result is not None
        assert result["handle"] == "TEST-ARIN"
        assert backend.api.org.from_handle.call_count == 3

    def test_get_organization_gives_up_after_max_retries(self):
        from netbox_rir_manager.backends.arin import ARINBackend

        backend = ARINBackend(api_key="test")
        backend.api.org.from_handle = MagicMock(
            side_effect=ConnectionError("timeout")
        )
        result = backend.get_organization("TEST-ARIN")
        assert result is None

    def test_get_poc_retries_on_exception(self):
        from netbox_rir_manager.backends.arin import ARINBackend

        backend = ARINBackend(api_key="test")
        mock_poc = MagicMock()
        mock_poc.handle = "JD1-ARIN"
        mock_poc.contact_type = "PERSON"
        mock_poc.first_name = "John"
        mock_poc.last_name = "Doe"
        mock_poc.company_name = ""
        mock_poc.emails = []
        mock_poc.phones = []
        mock_poc.city = ""
        mock_poc.postal_code = ""
        mock_poc.iso3166_1 = None

        backend.api.poc.from_handle = MagicMock(
            side_effect=[ConnectionError("fail"), mock_poc]
        )
        result = backend.get_poc("JD1-ARIN")
        assert result is not None
        assert backend.api.poc.from_handle.call_count == 2

    def test_find_net_retries_on_exception(self):
        from netbox_rir_manager.backends.arin import ARINBackend

        backend = ARINBackend(api_key="test")
        mock_net = MagicMock()
        mock_net.handle = "NET-1"
        mock_net.net_name = "TEST"
        mock_net.version = 4
        mock_net.org_handle = ""
        mock_net.parent_net_handle = ""
        mock_net.net_blocks = []

        backend.api.net.find_net = MagicMock(
            side_effect=[ConnectionError("fail"), mock_net]
        )
        result = backend.find_net("192.0.2.0", "192.0.2.255")
        assert result is not None
        assert backend.api.net.find_net.call_count == 2

    def test_no_retry_on_error_response(self):
        """Error objects from ARIN API should not trigger retries."""
        from netbox_rir_manager.backends.arin import ARINBackend

        backend = ARINBackend(api_key="test")
        backend.api.org.from_handle = MagicMock(return_value=Error())
        result = backend.get_organization("NOEXIST")
        assert result is None
        assert backend.api.org.from_handle.call_count == 1
```

**Step 3: Run tests to verify they fail**

Run: `pytest tests/test_backends/test_retry.py -v`
Expected: FAIL (no retry behavior)

**Step 4: Add retry logic to ARIN backend**

In `netbox_rir_manager/backends/arin.py`, add retry decorator using tenacity:

```python
import logging

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    retry=retry_if_exception_type((ConnectionError, OSError, TimeoutError)),
    reraise=False,
)
```

Apply `_retry` to the internal API call in each method. Since we need to return `None` on final failure (not raise), wrap the call:

Replace each public method (`get_organization`, `get_network`, `get_poc`, `find_net`, `authenticate`) to use a private retried helper. For example:

```python
def get_organization(self, handle: str) -> dict[str, Any] | None:
    try:
        result = self._call_with_retry(self.api.org.from_handle, handle)
    except Exception:
        logger.exception("Failed to retrieve organization %s after retries", handle)
        return None
    if isinstance(result, Error):
        return None
    return self._org_to_dict(result)

@_retry
def _call_with_retry(self, func, *args, **kwargs):
    return func(*args, **kwargs)
```

This is cleaner than decorating each method, since all methods have the same retry semantics: retry on connection errors, don't retry on `Error` responses.

**Step 5: Add plugin settings for retry config**

In `netbox_rir_manager/__init__.py`, add to `default_settings`:

```python
"api_retry_count": 3,
"api_retry_backoff": 2,
```

Update the ARIN backend to read these settings when constructing the retry decorator. Since tenacity decorators are configured at decoration time but we need runtime settings, use a method approach instead:

```python
def _call_with_retry(self, func, *args, **kwargs):
    from django.conf import settings as django_settings

    plugin_config = django_settings.PLUGINS_CONFIG.get("netbox_rir_manager", {})
    max_attempts = plugin_config.get("api_retry_count", 3)
    backoff = plugin_config.get("api_retry_backoff", 2)

    from tenacity import RetryError, Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

    try:
        for attempt in Retrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, max=backoff * max_attempts),
            retry=retry_if_exception_type((ConnectionError, OSError, TimeoutError)),
        ):
            with attempt:
                return func(*args, **kwargs)
    except RetryError:
        return None
```

**Step 6: Run tests**

```bash
pytest tests/test_backends/test_retry.py -v
pytest tests/ -v
```

Expected: ALL PASS

**Step 7: Commit**

```bash
git add pyproject.toml netbox_rir_manager/backends/arin.py netbox_rir_manager/__init__.py tests/test_backends/test_retry.py
git commit -m "feat: add tenacity retry with exponential backoff for ARIN API calls"
```

---

## Task 4: Add Scheduled Sync System Job

**Files:**
- Modify: `netbox_rir_manager/jobs.py`
- Modify: `tests/test_jobs.py`

**Step 1: Write failing tests**

Add to `tests/test_jobs.py`:

```python
@pytest.mark.django_db
class TestScheduledSyncJob:
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_all_active_configs(self, mock_backend_class, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob
        from netbox_rir_manager.models import RIROrganization

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = {
            "handle": "SCHED-ARIN",
            "name": "Scheduled Org",
            "street_address": "",
            "city": "",
            "state_province": "",
            "postal_code": "",
            "country": "",
            "poc_links": [],
            "raw_data": {},
        }
        mock_backend.find_net.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        job = MagicMock()
        job.data = {}
        runner = ScheduledRIRSyncJob.__new__(ScheduledRIRSyncJob)
        runner.job = job

        runner.run()

        assert RIROrganization.objects.filter(handle="SCHED-ARIN").exists()

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_skips_inactive_configs(self, mock_backend_class, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        rir_config.is_active = False
        rir_config.save()

        job = MagicMock()
        job.data = {}
        runner = ScheduledRIRSyncJob.__new__(ScheduledRIRSyncJob)
        runner.job = job

        runner.run()

        mock_backend_class.from_rir_config.assert_not_called()

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_skips_config_without_keys(self, mock_backend_class, rir_config):
        """Config without any RIRUserKey entries should be skipped."""
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        job = MagicMock()
        job.data = {}
        runner = ScheduledRIRSyncJob.__new__(ScheduledRIRSyncJob)
        runner.job = job

        runner.run()

        mock_backend_class.from_rir_config.assert_not_called()

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_groups_by_synced_by_key(
        self, mock_backend_class, rir_config, admin_user, rir_user_key
    ):
        """Objects with synced_by set should be refreshed using the same key."""
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob
        from netbox_rir_manager.models import RIROrganization

        # Create an org that was synced_by this user key
        RIROrganization.objects.create(
            rir_config=rir_config,
            handle="GROUPED-ARIN",
            name="Grouped Org",
            synced_by=rir_user_key,
        )

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = {
            "handle": "GROUPED-ARIN",
            "name": "Grouped Org Updated",
            "street_address": "",
            "city": "",
            "state_province": "",
            "postal_code": "",
            "country": "",
            "poc_links": [],
            "raw_data": {},
        }
        mock_backend.find_net.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        job = MagicMock()
        job.data = {}
        runner = ScheduledRIRSyncJob.__new__(ScheduledRIRSyncJob)
        runner.job = job

        runner.run()

        # Verify the backend was created with the correct key
        mock_backend_class.from_rir_config.assert_called_once_with(
            rir_config, api_key=rir_user_key.api_key
        )
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_jobs.py::TestScheduledSyncJob -v`
Expected: FAIL (ScheduledRIRSyncJob doesn't exist)

**Step 3: Implement ScheduledRIRSyncJob**

In `netbox_rir_manager/jobs.py`, add at the end of the file:

```python
from core.choices import JobIntervalChoices
from netbox.jobs import system_job


@system_job(interval=JobIntervalChoices.INTERVAL_DAILY)
class ScheduledRIRSyncJob(JobRunner):
    """Scheduled background job that syncs all active RIR configs."""

    class Meta:
        name = "Scheduled RIR Sync"

    def run(self, *args, **kwargs):
        from netbox_rir_manager.models import RIRConfig, RIRUserKey

        configs = RIRConfig.objects.filter(is_active=True)
        total_logs = 0

        for config in configs:
            # Collect distinct keys that have synced objects for this config
            synced_key_ids = set()
            for model_class in (RIROrganization, RIRContact, RIRNetwork):
                synced_key_ids.update(
                    model_class.objects.filter(
                        rir_config=config, synced_by__isnull=False
                    ).values_list("synced_by_id", flat=True).distinct()
                )

            if synced_key_ids:
                # Use keys that previously synced objects
                user_keys = RIRUserKey.objects.filter(pk__in=synced_key_ids)
            else:
                # Fallback: use first available key for this config
                user_keys = RIRUserKey.objects.filter(rir_config=config).order_by("pk")[:1]

            if not user_keys.exists():
                logger.warning("No API keys available for config %s, skipping", config.name)
                continue

            # Group sync by key — one backend instance per key
            for user_key in user_keys:
                try:
                    logs = sync_rir_config(
                        config, api_key=user_key.api_key, user_key=user_key
                    )
                    total_logs += len(logs)
                except Exception:
                    logger.exception(
                        "Scheduled sync failed for config %s with key %s",
                        config.name,
                        user_key.pk,
                    )

        self.job.data = {"configs_synced": len(configs), "total_logs": total_logs}
        self.job.save()
```

**Step 4: Run tests**

```bash
pytest tests/test_jobs.py -v
pytest tests/ -v
```

Expected: ALL PASS

**Step 5: Commit**

```bash
git add netbox_rir_manager/jobs.py tests/test_jobs.py
git commit -m "feat: add scheduled daily sync via @system_job"
```

---

## Task 5: Update Plugin Settings and Final Cleanup

**Files:**
- Modify: `netbox_rir_manager/__init__.py`
- All files: lint pass

**Step 1: Update default_settings**

In `netbox_rir_manager/__init__.py`, update `default_settings`:

```python
default_settings = {
    "top_level_menu": True,
    "sync_interval_hours": 24,
    "auto_link_networks": True,
    "enabled_backends": ["ARIN"],
    "encryption_key": "",  # defaults to SECRET_KEY if empty
    "api_retry_count": 3,
    "api_retry_backoff": 2,
}
```

**Step 2: Run linter**

```bash
ruff check --fix netbox_rir_manager/ tests/
ruff format netbox_rir_manager/ tests/
```

**Step 3: Run full test suite**

```bash
pytest tests/ -v --cov=netbox_rir_manager --cov-report=term-missing
```

**Step 4: Run Django checks**

```bash
python /opt/netbox/netbox/manage.py check
python /opt/netbox/netbox/manage.py makemigrations --check --dry-run
```

**Step 5: Commit**

```bash
git add -A
git commit -m "chore: add plugin settings for encryption and retry, final lint pass"
```

---

## Summary of Changes

| Component | Change |
|---|---|
| `fields.py` | New `EncryptedCharField` using Fernet + HKDF-SHA256 |
| `models/credentials.py` | `api_key` changed to `EncryptedCharField(max_length=512)` |
| `models/resources.py` | `synced_by` FK to `RIRUserKey` on Organization, Contact, Network (hidden, editable=False) |
| `jobs.py` | `sync_rir_config` accepts `user_key` param, sets `synced_by`. New `ScheduledRIRSyncJob` with `@system_job(1440)` |
| `backends/arin.py` | `_call_with_retry` using tenacity for exponential backoff on connection errors |
| `__init__.py` | New settings: `encryption_key`, `api_retry_count`, `api_retry_backoff` |
| `pyproject.toml` | Added `tenacity>=8.0` dependency |

## New Dependencies

| Package | Purpose |
|---|---|
| `tenacity>=8.0` | Retry with exponential backoff |
| `cryptography` (already installed) | Fernet encryption + HKDF key derivation |
