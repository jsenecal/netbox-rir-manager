from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from typing import TYPE_CHECKING

from core.choices import JobIntervalChoices
from django.contrib.auth import get_user_model
from django.utils import timezone
from netbox.jobs import JobRunner, system_job
from utilities.request import NetBoxFakeRequest, apply_request_processors

from netbox_rir_manager.backends.arin import ARINBackend
from netbox_rir_manager.models import RIRContact, RIRCustomer, RIRNetwork, RIROrganization, RIRSyncLog

if TYPE_CHECKING:
    from netbox_rir_manager.models import RIRConfig, RIRUserKey

logger = logging.getLogger(__name__)


@contextmanager
def _changelog_context(user):
    """Context manager that enables change logging if a valid user is available."""
    User = get_user_model()
    if user is not None and isinstance(user, User):
        request = NetBoxFakeRequest({
            "META": {},
            "POST": {},
            "GET": {},
            "FILES": {},
            "user": user,
            "path": "",
            "id": uuid.uuid4(),
        })
        with apply_request_processors(request):
            yield
    else:
        yield


def sync_rir_config(
    rir_config: RIRConfig,
    api_key: str,
    resource_types: list[str] | None = None,
    user_key: RIRUserKey | None = None,
    log: logging.Logger = logger,
) -> tuple[list[RIRSyncLog], list[tuple]]:
    """
    Sync RIR data for the given config.
    resource_types: list of "organizations", "contacts", "networks". None = all.
    Returns (sync_logs, agg_nets) where agg_nets is a list of (Aggregate, RIRNetwork) tuples.
    """
    logs: list[RIRSyncLog] = []
    agg_nets: list[tuple] = []
    backend = ARINBackend.from_rir_config(rir_config, api_key=api_key)

    types_to_sync = resource_types or ["organizations", "contacts", "networks"]
    log.info(f"Starting sync for {rir_config.name} (types: {', '.join(types_to_sync)})")

    org = None
    if "organizations" in types_to_sync and rir_config.org_handle:
        log.info(f"Syncing organization {rir_config.org_handle}")
        org_logs, org = _sync_organization(backend, rir_config, user_key=user_key, log=log)
        logs.extend(org_logs)

    if "contacts" in types_to_sync and org:
        poc_links = (org.raw_data or {}).get("poc_links", [])
        log.info(f"Syncing {len(poc_links)} contacts")
        logs.extend(_sync_contacts(backend, rir_config, poc_links, org, user_key=user_key, log=log))

    if "networks" in types_to_sync:
        log.info("Syncing aggregate-level networks")
        net_logs, agg_nets = _sync_aggregate_nets(backend, rir_config, user_key=user_key, log=log)
        logs.extend(net_logs)

    rir_config.last_sync = timezone.now()
    rir_config.save(update_fields=["last_sync"])

    log.info(f"Sync complete: {len(logs)} log entries, {len(agg_nets)} aggregates with networks")
    return logs, agg_nets


def _sync_organization(
    backend: ARINBackend,
    rir_config: RIRConfig,
    user_key: RIRUserKey | None = None,
    log: logging.Logger = logger,
) -> tuple[list[RIRSyncLog], RIROrganization | None]:
    """Sync the primary organization for a config."""
    logs: list[RIRSyncLog] = []

    log.info(f"Fetching organization {rir_config.org_handle} from ARIN")
    org_data = backend.get_organization(rir_config.org_handle)
    if org_data is None:
        log.warning(f"Failed to retrieve organization {rir_config.org_handle} from ARIN")
        sync_log = RIRSyncLog.objects.create(
            rir_config=rir_config,
            operation="sync",
            object_type="organization",
            object_handle=rir_config.org_handle,
            status="error",
            message=f"Failed to retrieve organization {rir_config.org_handle}",
        )
        logs.append(sync_log)
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

    log.info(f"{'Created' if created else 'Updated'} organization {org_data['handle']}")

    sync_log = RIRSyncLog.objects.create(
        rir_config=rir_config,
        operation="sync",
        object_type="organization",
        object_handle=org_data["handle"],
        status="success",
        message=f"{'Created' if created else 'Updated'} organization {org_data['handle']}",
    )
    logs.append(sync_log)

    return logs, org


def _sync_contacts(
    backend: ARINBackend,
    rir_config: RIRConfig,
    poc_links: list[dict],
    org: RIROrganization,
    user_key: RIRUserKey | None = None,
    log: logging.Logger = logger,
) -> list[RIRSyncLog]:
    """Sync POC contacts from org poc_links."""
    logs: list[RIRSyncLog] = []
    log.info(f"Syncing {len(poc_links)} POC contacts for {org.handle}")

    for link in poc_links:
        handle = link.get("handle")
        if not handle:
            continue

        log.debug(f"Fetching POC {handle}")
        poc_data = backend.get_poc(handle)
        if poc_data is None:
            log.warning(f"Failed to retrieve POC {handle}")
            sync_log = RIRSyncLog.objects.create(
                rir_config=rir_config,
                operation="sync",
                object_type="contact",
                object_handle=handle,
                status="error",
                message=f"Failed to retrieve POC {handle}",
            )
            logs.append(sync_log)
            continue

        contact, created = RIRContact.objects.update_or_create(
            handle=poc_data["handle"],
            defaults={
                "rir_config": rir_config,
                "contact_type": poc_data.get("contact_type") or "",
                "first_name": poc_data.get("first_name") or "",
                "last_name": poc_data.get("last_name") or "",
                "company_name": poc_data.get("company_name") or "",
                "email": poc_data.get("email") or "",
                "phone": poc_data.get("phone") or "",
                "street_address": poc_data.get("street_address") or "",
                "city": poc_data.get("city") or "",
                "state_province": poc_data.get("state_province") or "",
                "postal_code": poc_data.get("postal_code") or "",
                "country": poc_data.get("country") or "",
                "organization": org,
                "raw_data": poc_data.get("raw_data") or {},
                "last_synced": timezone.now(),
                "synced_by": user_key,
            },
        )

        log.info(f"{'Created' if created else 'Updated'} contact {poc_data['handle']}")
        sync_log = RIRSyncLog.objects.create(
            rir_config=rir_config,
            operation="sync",
            object_type="contact",
            object_handle=poc_data["handle"],
            status="success",
            message=f"{'Created' if created else 'Updated'} contact {poc_data['handle']}",
        )
        logs.append(sync_log)

    return logs


def _sync_customer_for_net(
    backend: ARINBackend,
    rir_config: RIRConfig,
    net_data: dict,
    network: RIRNetwork,
    user_key: RIRUserKey | None = None,
    log: logging.Logger = logger,
) -> RIRSyncLog | None:
    """If net_data has a customer_handle, fetch and persist the customer."""
    customer_handle = net_data.get("customer_handle")
    if not customer_handle:
        return None

    log.debug(f"Fetching customer {customer_handle}")
    cust_data = backend.get_customer(customer_handle)
    if cust_data is None:
        log.warning(f"Failed to retrieve customer {customer_handle}")
        return RIRSyncLog.objects.create(
            rir_config=rir_config,
            operation="sync",
            object_type="customer",
            object_handle=customer_handle,
            status="error",
            message=f"Failed to retrieve customer {customer_handle}",
        )

    reg_date = cust_data.get("registration_date")
    if reg_date:
        import datetime as dt

        try:
            created_date = dt.datetime.fromisoformat(reg_date).replace(tzinfo=dt.UTC)
        except (ValueError, TypeError):
            created_date = timezone.now()
    else:
        created_date = timezone.now()

    _customer, created = RIRCustomer.objects.update_or_create(
        handle=cust_data["handle"],
        defaults={
            "rir_config": rir_config,
            "customer_name": cust_data.get("customer_name", ""),
            "street_address": cust_data.get("street_address", ""),
            "city": cust_data.get("city", ""),
            "state_province": cust_data.get("state_province", ""),
            "postal_code": cust_data.get("postal_code", ""),
            "country": cust_data.get("country", ""),
            "network": network,
            "raw_data": cust_data,
            "created_date": created_date,
        },
    )

    log.info(f"{'Created' if created else 'Updated'} customer {cust_data['handle']}")
    return RIRSyncLog.objects.create(
        rir_config=rir_config,
        operation="sync",
        object_type="customer",
        object_handle=cust_data["handle"],
        status="success",
        message=f"{'Created' if created else 'Updated'} customer {cust_data['handle']}",
    )


def _sync_aggregate_nets(
    backend: ARINBackend,
    rir_config: RIRConfig,
    user_key: RIRUserKey | None = None,
    log: logging.Logger = logger,
) -> tuple[list[RIRSyncLog], list[tuple]]:
    """Sync aggregate-level networks. Returns (logs, agg_nets) for prefix fan-out."""
    from ipam.models import Aggregate

    logs: list[RIRSyncLog] = []
    agg_nets: list[tuple] = []

    aggregates = Aggregate.objects.filter(rir=rir_config.rir)
    log.info(f"Found {aggregates.count()} aggregates to sync")

    for agg in aggregates:
        network = agg.prefix
        start_address = str(network.network)
        end_address = str(network.broadcast)

        log.debug(f"Querying ARIN for aggregate {agg.prefix}")
        net_data = backend.find_net(start_address, end_address)
        if net_data is None:
            log.warning(f"No ARIN network found for aggregate {agg.prefix}")
            continue

        parent_net, created = RIRNetwork.sync_from_arin(
            net_data, rir_config, aggregate=agg, user_key=user_key,
        )
        log.info(f"{'Created' if created else 'Updated'} network {net_data['handle']} for aggregate {agg.prefix}")

        sync_log = RIRSyncLog.objects.create(
            rir_config=rir_config,
            operation="sync",
            object_type="network",
            object_handle=net_data["handle"],
            status="success",
            message=f"{'Created' if created else 'Updated'} network {net_data['handle']}",
        )
        logs.append(sync_log)
        agg_nets.append((agg, parent_net))

        cust_log = _sync_customer_for_net(backend, rir_config, net_data, parent_net, user_key=user_key, log=log)
        if cust_log:
            logs.append(cust_log)

    return logs, agg_nets


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

        self.logger.info(f"Starting RIR sync for {rir_config.name}")
        with _changelog_context(self.job.user):
            logs, agg_nets = sync_rir_config(rir_config, api_key=user_key.api_key, user_key=user_key, log=self.logger)

        # Enqueue per-aggregate prefix discovery sub-jobs
        for agg, parent_net in agg_nets:
            SyncPrefixesJob.enqueue(
                instance=rir_config,
                user=user_key.user,
                aggregate_id=agg.pk,
                parent_handle=parent_net.handle,
                user_key_id=user_key.pk,
            )
            self.logger.info(f"Enqueued prefix sync for aggregate {agg.prefix}")

        self.job.data["sync_logs_count"] = len(logs)
        self.job.save()
        self.logger.info(f"Sync complete: {len(logs)} log entries")


class SyncPrefixesJob(JobRunner):
    """Discover and sync child prefix reassignments for a single aggregate."""

    class Meta:
        name = "ARIN Prefix Sync"

    def run(self, *args, **kwargs):
        from ipam.models import Aggregate, Prefix

        from netbox_rir_manager.models import RIRUserKey

        aggregate_id = kwargs["aggregate_id"]
        parent_handle = kwargs["parent_handle"]
        user_key_id = kwargs["user_key_id"]

        agg = Aggregate.objects.get(pk=aggregate_id)
        user_key = RIRUserKey.objects.get(pk=user_key_id)
        parent_net = RIRNetwork.objects.get(handle=parent_handle)
        rir_config = parent_net.rir_config
        backend = ARINBackend.from_rir_config(rir_config, api_key=user_key.api_key)

        prefixes = Prefix.objects.filter(prefix__net_contained=agg.prefix)
        self.logger.info(f"Scanning {prefixes.count()} prefixes under {agg.prefix}")

        with _changelog_context(self.job.user):
            for pfx in prefixes:
                pfx_network = pfx.prefix
                pfx_start = str(pfx_network.network)
                pfx_end = str(pfx_network.broadcast)

                self.logger.debug(f"Querying ARIN for prefix {pfx.prefix}")
                pfx_net_data = backend.find_net(pfx_start, pfx_end)
                if pfx_net_data is None:
                    continue

                if pfx_net_data["handle"] == parent_handle:
                    self.logger.debug(f"Prefix {pfx.prefix} returns parent net, skipping")
                    continue

                _net, created = RIRNetwork.sync_from_arin(
                    pfx_net_data, rir_config, prefix=pfx, user_key=user_key,
                )
                self.logger.info(
                    f"{'Created' if created else 'Updated'} network {pfx_net_data['handle']} for prefix {pfx.prefix}"
                )

                RIRSyncLog.objects.create(
                    rir_config=rir_config,
                    operation="sync",
                    object_type="network",
                    object_handle=pfx_net_data["handle"],
                    status="success",
                    message=(
                        f"{'Created' if created else 'Updated'} network "
                        f"{pfx_net_data['handle']} for prefix {pfx.prefix}"
                    ),
                )

                _sync_customer_for_net(
                    backend, rir_config, pfx_net_data, _net, user_key=user_key, log=self.logger,
                )


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
        self.logger.info(f"Starting reassignment for prefix {prefix.prefix}")

        with _changelog_context(self.job.user):
            # Find the parent RIRNetwork via Aggregate
            agg = Aggregate.objects.filter(
                prefix__net_contains_or_equals=prefix.prefix
            ).first()
            if not agg:
                self.logger.error(f"No matching Aggregate found for prefix {prefix.prefix}")
                self.job.data["status"] = "error"
                self.job.data["message"] = "No matching Aggregate found"
                self.job.save()
                return

            parent_network = RIRNetwork.objects.filter(aggregate=agg, auto_reassign=True).first()
            if not parent_network:
                self.logger.error(f"No parent RIRNetwork with auto_reassign=True for aggregate {agg.prefix}")
                self.job.data["status"] = "error"
                self.job.data["message"] = "No parent RIRNetwork with auto_reassign=True"
                self.job.save()
                return

            self.logger.info(f"Found parent network {parent_network.handle} (aggregate {agg.prefix})")
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

            # Pre-flight: check what ARIN actually has for this range
            self.logger.info(f"Pre-flight: querying ARIN for existing net at {start_address}-{end_address}")
            actual_net = backend.find_net(start_address, end_address)
            if actual_net is not None:
                actual_handle = actual_net.get("handle")

                # Already reassigned at ARIN (different net than parent) -- just sync it
                if actual_handle and actual_handle != parent_network.handle:
                    self.logger.warning(
                        f"Pre-flight: prefix already reassigned as {actual_handle}, syncing instead"
                    )
                    RIRNetwork.sync_from_arin(
                        actual_net, rir_config, prefix=prefix, user_key=user_key,
                    )
                    self.job.data["status"] = "synced"
                    self.job.data["message"] = (
                        f"Prefix already has ARIN network {actual_handle} "
                        f"(expected parent {parent_network.handle}). Synced locally."
                    )
                    self.job.save()

                    RIRSyncLog.objects.create(
                        rir_config=rir_config,
                        operation="reassign",
                        object_type="network",
                        object_handle=actual_handle,
                        status="skipped",
                        message=(
                            f"Prefix {prefix.prefix} already reassigned at ARIN as "
                            f"{actual_handle}. Synced instead of re-reassigning."
                        ),
                    )
                    return

            self.logger.info("Pre-flight passed")

            self.logger.info(f"Reassignment type: {'detailed' if rir_org else 'simple'}")

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

                RIRCustomer.objects.create(
                    rir_config=rir_config,
                    handle=customer_result["handle"],
                    customer_name=tenant.name,
                    street_address=site_address.street_address,
                    city=site_address.city,
                    state_province=site_address.state_province,
                    postal_code=site_address.postal_code,
                    country=site_address.country,
                    network=parent_network,
                    tenant=tenant,
                    raw_data=customer_result,
                    created_date=timezone.now(),
                )

                net_data = {
                    "customer_handle": customer_result["handle"],
                    "net_name": f"{tenant.name}-{prefix.prefix}",
                    "start_address": start_address,
                    "end_address": end_address,
                }

            # Perform the reassignment
            self.logger.info(f"Submitting reassignment to ARIN for {prefix.prefix}")
            result = backend.reassign_network(parent_network.handle, net_data)
            if result is None:
                self.logger.error(f"Reassignment failed at ARIN for prefix {prefix.prefix}")
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
                RIRNetwork.sync_from_arin(
                    net_result, rir_config, prefix=prefix, user_key=user_key,
                )

            RIRSyncLog.objects.create(
                rir_config=rir_config,
                operation="reassign",
                object_type="network",
                object_handle=parent_network.handle,
                status="success",
                message=f"Reassignment submitted for {prefix.prefix}, ticket {ticket.ticket_number}",
            )

            self.logger.info(f"Reassignment submitted, ticket {ticket.ticket_number}")
            self.job.data["status"] = "success"
            self.job.data["ticket_number"] = ticket.ticket_number
            self.job.save()


class RemoveNetworkJob(JobRunner):
    """Background job for removing a reassigned network at ARIN."""

    class Meta:
        name = "ARIN Remove"

    def run(self, *args, **kwargs):
        from netbox_rir_manager.models import RIRUserKey

        network_id = kwargs.get("network_id")
        user_key_id = kwargs.get("user_key_id")

        network = RIRNetwork.objects.get(pk=network_id)
        user_key = RIRUserKey.objects.get(pk=user_key_id)

        self.job.data = {"network_handle": network.handle, "status": "starting"}
        self.job.save()

        self.logger.info(f"Removing network {network.handle} from ARIN")
        rir_config = network.rir_config
        backend = ARINBackend.from_rir_config(rir_config, api_key=user_key.api_key)

        success = backend.remove_network(network.handle)

        if success:
            self.logger.info(f"Successfully removed network {network.handle}")
        else:
            self.logger.error(f"Failed to remove network {network.handle}")

        status = "success" if success else "error"
        message = (
            f"Removed network {network.handle} from ARIN"
            if success
            else f"Failed to remove network {network.handle} from ARIN"
        )

        with _changelog_context(self.job.user):
            RIRSyncLog.objects.create(
                rir_config=rir_config,
                operation="remove",
                object_type="network",
                object_handle=network.handle,
                status=status,
                message=message,
            )

        self.job.data["status"] = status
        if not success:
            self.job.data["message"] = "ARIN removal failed"
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
        self.logger.info(f"Starting scheduled sync for {configs.count()} active configs")

        with _changelog_context(self.job.user):
            for config in configs:
                self.logger.info(f"Syncing config: {config.name}")

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
                    self.logger.warning(f"No API keys for config {config.name}, skipping")
                    continue

                for user_key in user_keys:
                    self.logger.info(f"Using API key {user_key.pk} for config {config.name}")
                    try:
                        logs, _agg_nets = sync_rir_config(
                            config, api_key=user_key.api_key, user_key=user_key, log=self.logger
                        )
                        total_logs += len(logs)
                    except Exception:
                        self.logger.exception(
                            f"Scheduled sync failed for config {config.name} with key {user_key.pk}"
                        )

        self.logger.info(f"Scheduled sync complete: {configs.count()} configs, {total_logs} logs")
        self.job.data = {"configs_synced": len(configs), "total_logs": total_logs}
        self.job.save()
