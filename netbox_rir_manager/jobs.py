from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.choices import JobIntervalChoices
from django.utils import timezone
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
                "street_address": poc_data.get("street_address", ""),
                "city": poc_data.get("city", ""),
                "state_province": poc_data.get("state_province", ""),
                "postal_code": poc_data.get("postal_code", ""),
                "country": poc_data.get("country", ""),
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
                "net_type": net_data.get("net_type", ""),
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


class ReassignJob(JobRunner):
    """Background job for reassigning a prefix at ARIN.

    Accepts prefix_id and user_key_id via kwargs.
    Determines simple vs detailed based on whether the prefix's tenant
    has a linked RIROrganization.
    """

    class Meta:
        name = "ARIN Reassign"

    def run(self, *args, **kwargs):
        from ipam.models import Aggregate, Prefix

        from netbox_rir_manager.choices import normalize_ticket_status
        from netbox_rir_manager.models import RIRSiteAddress, RIRTicket, RIRUserKey
        from netbox_rir_manager.services.geocoding import resolve_site_address

        prefix_id = kwargs.get("prefix_id")
        user_key_id = kwargs.get("user_key_id")

        prefix = Prefix.objects.get(pk=prefix_id)
        user_key = RIRUserKey.objects.get(pk=user_key_id)

        self.job.data = {"prefix": str(prefix.prefix), "status": "starting"}
        self.job.save()

        # Find the parent RIRNetwork via Aggregate
        agg = Aggregate.objects.filter(
            prefix__net_contains_or_equals=prefix.prefix
        ).first()
        if not agg:
            self.job.data["status"] = "error"
            self.job.data["message"] = "No matching Aggregate found"
            self.job.save()
            return

        parent_network = RIRNetwork.objects.filter(aggregate=agg, auto_reassign=True).first()
        if not parent_network:
            self.job.data["status"] = "error"
            self.job.data["message"] = "No parent RIRNetwork with auto_reassign=True"
            self.job.save()
            return

        rir_config = parent_network.rir_config
        backend = ARINBackend.from_rir_config(rir_config, api_key=user_key.api_key)

        # Determine reassignment type
        tenant = prefix.tenant
        rir_org = RIROrganization.objects.filter(tenant=tenant).first() if tenant else None

        # Compute subnet range from prefix
        import ipaddress

        network = ipaddress.ip_network(str(prefix.prefix), strict=False)
        start_address = str(network.network_address)
        end_address = str(network.broadcast_address)

        if rir_org:
            # Detailed reassignment - tenant has a known RIR org
            self.job.data["reassignment_type"] = "detailed"
            self.job.data["org_handle"] = rir_org.handle
            self.job.save()

            net_data = {
                "org_handle": rir_org.handle,
                "net_name": f"{tenant.name}-{prefix.prefix}",
                "start_address": start_address,
                "end_address": end_address,
            }
        else:
            # Simple reassignment - create customer from site address
            self.job.data["reassignment_type"] = "simple"
            self.job.save()

            # Get the site - use scope for GenericFK
            site = getattr(prefix, "_site", None) or getattr(prefix, "site", None)
            if site is None:
                # Try scope
                scope = getattr(prefix, "scope", None)
                from dcim.models import Site

                if isinstance(scope, Site):
                    site = scope

            if not site:
                self.job.data["status"] = "error"
                self.job.data["message"] = "Prefix has no site"
                self.job.save()
                return

            # Resolve site address
            try:
                site_address = site.rir_address
            except RIRSiteAddress.DoesNotExist:
                site_address = resolve_site_address(site)

            if not site_address:
                self.job.data["status"] = "error"
                self.job.data["message"] = "Could not resolve address for site"
                self.job.save()
                return

            # Create customer at ARIN
            customer_data = {
                "customer_name": tenant.name,
                "street_address": site_address.street_address,
                "city": site_address.city,
                "state_province": site_address.state_province,
                "postal_code": site_address.postal_code,
                "country": site_address.country,
            }
            customer_result = backend.create_customer(parent_network.handle, customer_data)
            if customer_result is None:
                RIRSyncLog.objects.create(
                    rir_config=rir_config,
                    operation="create",
                    object_type="customer",
                    object_handle=parent_network.handle,
                    status="error",
                    message=f"Failed to create customer for {tenant.name}",
                )
                self.job.data["status"] = "error"
                self.job.data["message"] = "Failed to create customer at ARIN"
                self.job.save()
                return

            net_data = {
                "customer_handle": customer_result["handle"],
                "net_name": f"{tenant.name}-{prefix.prefix}",
                "start_address": start_address,
                "end_address": end_address,
            }

        # Perform the reassignment
        result = backend.reassign_network(parent_network.handle, net_data)
        if result is None:
            RIRSyncLog.objects.create(
                rir_config=rir_config,
                operation="reassign",
                object_type="network",
                object_handle=parent_network.handle,
                status="error",
                message=f"Reassignment failed for prefix {prefix.prefix}",
            )
            self.job.data["status"] = "error"
            self.job.data["message"] = "Reassignment failed at ARIN"
            self.job.save()
            return

        # Create ticket record
        ticket = RIRTicket.objects.create(
            rir_config=rir_config,
            ticket_number=result.get("ticket_number", ""),
            ticket_type=result.get("ticket_type", "IPV4_SIMPLE_REASSIGN"),
            status=normalize_ticket_status(result.get("ticket_status", "")),
            network=parent_network,
            submitted_by=user_key,
            created_date=timezone.now(),
            raw_data=result.get("raw_data", {}),
        )

        # Create child RIRNetwork if net data was returned
        net_result = result.get("net")
        if net_result and net_result.get("handle"):
            RIRNetwork.objects.update_or_create(
                handle=net_result["handle"],
                defaults={
                    "rir_config": rir_config,
                    "net_name": net_result.get("net_name", ""),
                    "net_type": net_result.get("net_type", ""),
                    "organization": rir_org,
                    "prefix": prefix,
                    "raw_data": net_result,
                    "last_synced": timezone.now(),
                    "synced_by": user_key,
                },
            )

        RIRSyncLog.objects.create(
            rir_config=rir_config,
            operation="reassign",
            object_type="network",
            object_handle=parent_network.handle,
            status="success",
            message=f"Reassignment submitted for {prefix.prefix}, ticket {ticket.ticket_number}",
        )

        self.job.data["status"] = "success"
        self.job.data["ticket_number"] = ticket.ticket_number
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
                    model_class.objects.filter(rir_config=config, synced_by__isnull=False)
                    .values_list("synced_by_id", flat=True)
                    .distinct()
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
                    logs = sync_rir_config(config, api_key=user_key.api_key, user_key=user_key)
                    total_logs += len(logs)
                except Exception:
                    logger.exception(
                        "Scheduled sync failed for config %s with key %s",
                        config.name,
                        user_key.pk,
                    )

        self.job.data = {"configs_synced": len(configs), "total_logs": total_logs}
        self.job.save()
