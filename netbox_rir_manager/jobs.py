from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.utils import timezone

from netbox_rir_manager.backends.arin import ARINBackend
from netbox_rir_manager.models import RIROrganization, RIRSyncLog

if TYPE_CHECKING:
    from netbox_rir_manager.models import RIRConfig

logger = logging.getLogger(__name__)


def sync_rir_config(rir_config: RIRConfig, resource_types: list[str] | None = None) -> list[RIRSyncLog]:
    """
    Sync RIR data for the given config.
    resource_types: list of "organizations", "contacts", "networks". None = all.
    """
    logs: list[RIRSyncLog] = []
    backend = ARINBackend.from_rir_config(rir_config)

    types_to_sync = resource_types or ["organizations", "contacts", "networks"]

    if "organizations" in types_to_sync and rir_config.org_handle:
        logs.extend(_sync_organization(backend, rir_config))

    rir_config.last_sync = timezone.now()
    rir_config.save(update_fields=["last_sync"])

    return logs


def _sync_organization(backend: ARINBackend, rir_config: RIRConfig) -> list[RIRSyncLog]:
    """Sync the primary organization for a config."""
    logs: list[RIRSyncLog] = []

    org_data = backend.get_organization(rir_config.org_handle)
    if org_data is None:
        log = RIRSyncLog.objects.create(
            rir_config=rir_config,
            operation="sync",
            object_type="organization",
            object_handle=rir_config.org_handle,
            status="error",
            message=f"Failed to retrieve organization {rir_config.org_handle}",
        )
        logs.append(log)
        return logs

    org, created = RIROrganization.objects.update_or_create(
        handle=org_data["handle"],
        defaults={
            "rir_config": rir_config,
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
        rir_config=rir_config,
        operation="sync",
        object_type="organization",
        object_handle=org_data["handle"],
        status="success",
        message=f"{'Created' if created else 'Updated'} organization {org_data['handle']}",
    )
    logs.append(log)

    return logs
