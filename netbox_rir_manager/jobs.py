from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.utils import timezone
from core.choices import JobIntervalChoices
from netbox.jobs import JobRunner, system_job

from netbox_rir_manager.backends.arin import ARINBackend
from netbox_rir_manager.models import RIRContact, RIRNetwork, RIROrganization, RIRSyncLog

if TYPE_CHECKING:
    from netbox_rir_manager.models import RIRConfig, RIRUserKey

logger = logging.getLogger(__name__)


def sync_rir_config(
    rir_config: RIRConfig,
    api_key: str,
    resource_types: list[str] | None = None,
    user_key: RIRUserKey | None = None,
) -> list[RIRSyncLog]:
    """
    Sync RIR data for the given config.
    resource_types: list of "organizations", "contacts", "networks". None = all.
    """
    logs: list[RIRSyncLog] = []
    backend = ARINBackend.from_rir_config(rir_config, api_key=api_key)

    types_to_sync = resource_types or ["organizations", "contacts", "networks"]

    org = None
    if "organizations" in types_to_sync and rir_config.org_handle:
        org_logs, org = _sync_organization(backend, rir_config, user_key=user_key)
        logs.extend(org_logs)

    if "contacts" in types_to_sync and org:
        poc_links = (org.raw_data or {}).get("poc_links", [])
        logs.extend(_sync_contacts(backend, rir_config, poc_links, org, user_key=user_key))

    if "networks" in types_to_sync:
        logs.extend(_sync_networks(backend, rir_config, user_key=user_key))

    rir_config.last_sync = timezone.now()
    rir_config.save(update_fields=["last_sync"])

    return logs


def _sync_organization(
    backend: ARINBackend, rir_config: RIRConfig, user_key: RIRUserKey | None = None
) -> tuple[list[RIRSyncLog], RIROrganization | None]:
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
        return logs, None

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
            "raw_data": org_data,
            "last_synced": timezone.now(),
            "synced_by": user_key,
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

    return logs, org


def _sync_contacts(
    backend: ARINBackend,
    rir_config: RIRConfig,
    poc_links: list[dict],
    org: RIROrganization,
    user_key: RIRUserKey | None = None,
) -> list[RIRSyncLog]:
    """Sync POC contacts from org poc_links."""
    logs: list[RIRSyncLog] = []

    for link in poc_links:
        handle = link.get("handle")
        if not handle:
            continue

        poc_data = backend.get_poc(handle)
        if poc_data is None:
            log = RIRSyncLog.objects.create(
                rir_config=rir_config,
                operation="sync",
                object_type="contact",
                object_handle=handle,
                status="error",
                message=f"Failed to retrieve POC {handle}",
            )
            logs.append(log)
            continue

        contact, created = RIRContact.objects.update_or_create(
            handle=poc_data["handle"],
            defaults={
                "rir_config": rir_config,
                "contact_type": poc_data.get("contact_type", ""),
                "first_name": poc_data.get("first_name", ""),
                "last_name": poc_data.get("last_name", ""),
                "company_name": poc_data.get("company_name", ""),
                "email": poc_data.get("email", ""),
                "phone": poc_data.get("phone", ""),
                "organization": org,
                "raw_data": poc_data.get("raw_data", {}),
                "last_synced": timezone.now(),
                "synced_by": user_key,
            },
        )

        log = RIRSyncLog.objects.create(
            rir_config=rir_config,
            operation="sync",
            object_type="contact",
            object_handle=poc_data["handle"],
            status="success",
            message=f"{'Created' if created else 'Updated'} contact {poc_data['handle']}",
        )
        logs.append(log)

    return logs


def _sync_networks(backend: ARINBackend, rir_config: RIRConfig, user_key: RIRUserKey | None = None) -> list[RIRSyncLog]:
    """Sync networks by matching NetBox IPAM Aggregates against ARIN."""
    from ipam.models import Aggregate

    logs: list[RIRSyncLog] = []

    aggregates = Aggregate.objects.filter(rir=rir_config.rir)
    for agg in aggregates:
        network = agg.prefix
        start_address = str(network.network)
        end_address = str(network.broadcast)

        net_data = backend.find_net(start_address, end_address)
        if net_data is None:
            continue

        # Try to find the org
        org = None
        org_handle = net_data.get("org_handle")
        if org_handle:
            org = RIROrganization.objects.filter(handle=org_handle).first()

        net, created = RIRNetwork.objects.update_or_create(
            handle=net_data["handle"],
            defaults={
                "rir_config": rir_config,
                "net_name": net_data.get("net_name", ""),
                "organization": org,
                "aggregate": agg,
                "raw_data": net_data,
                "last_synced": timezone.now(),
                "synced_by": user_key,
            },
        )

        log = RIRSyncLog.objects.create(
            rir_config=rir_config,
            operation="sync",
            object_type="network",
            object_handle=net_data["handle"],
            status="success",
            message=f"{'Created' if created else 'Updated'} network {net_data['handle']}",
        )
        logs.append(log)

    return logs


class SyncRIRConfigJob(JobRunner):
    """Background job for syncing RIR data."""

    class Meta:
        name = "RIR Sync"

    def run(self, *args, **kwargs):
        from netbox_rir_manager.models import RIRConfig, RIRUserKey

        rir_config = RIRConfig.objects.get(pk=self.job.object_id)
        user_id = kwargs.get("user_id") or (args[0] if args else None)

        user_key = RIRUserKey.objects.get(user_id=user_id, rir_config=rir_config)

        self.job.data = {"rir_config": rir_config.name}
        self.job.save()

        logs = sync_rir_config(rir_config, api_key=user_key.api_key, user_key=user_key)
        self.job.data["sync_logs_count"] = len(logs)
        self.job.save()


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
                user_keys = RIRUserKey.objects.filter(pk__in=synced_key_ids)
            else:
                user_keys = RIRUserKey.objects.filter(rir_config=config).order_by("pk")[:1]

            if not user_keys.exists():
                logger.warning("No API keys available for config %s, skipping", config.name)
                continue

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
