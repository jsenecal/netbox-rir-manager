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
from netbox_rir_manager.ip_ranges import prefix_range
from netbox_rir_manager.models import RIRAddress, RIRContact, RIRCustomer, RIRNetwork, RIROrganization, RIRSyncLog
from netbox_rir_manager.net_names import build_net_name

if TYPE_CHECKING:
    from netbox_rir_manager.models import RIRConfig, RIRUserKey

logger = logging.getLogger(__name__)


@contextmanager
def _changelog_context(user):
    """Context manager that enables change logging if a valid user is available."""
    User = get_user_model()
    if user is not None and isinstance(user, User):
        request = NetBoxFakeRequest(
            {
                "META": {},
                "POST": {},
                "GET": {},
                "FILES": {},
                "user": user,
                "path": "",
                "id": uuid.uuid4(),
            }
        )
        with apply_request_processors(request):
            yield
    else:
        yield


def _queued_user_key(runner: JobRunner, user_key_id: int, operation: str, object_handle: str) -> RIRUserKey | None:
    """Load the key a job was queued with, or None if it may no longer be used.

    The owner may have been deactivated since the job was queued. In that case the job is
    marked skipped and a skipped sync log records why, so no RIR call is made with the key.
    """
    from netbox_rir_manager.models import RIRUserKey

    user_key = RIRUserKey.objects.select_related("user", "rir_config").get(pk=user_key_id)
    if user_key.user.is_active:
        return user_key

    reason = user_key.rir_config.no_key_reason(user_key.user)
    runner.logger.warning(reason)
    runner.job.data = {"status": "skipped", "message": reason}
    runner.job.save()
    RIRSyncLog.log_skipped(user_key.rir_config, operation, object_handle, reason)
    return None


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

    # Build address data from org_data
    address_data = {
        "street_address": org_data.get("street_address", ""),
        "city": org_data.get("city", ""),
        "state_province": org_data.get("state_province", ""),
        "postal_code": org_data.get("postal_code", ""),
        "country": org_data.get("country", ""),
    }
    has_address = any(address_data.values())

    org, created = RIROrganization.objects.update_or_create(
        handle=org_data["handle"],
        defaults={
            "rir_config": rir_config,
            "name": org_data.get("name", ""),
            "raw_data": org_data,
            "last_synced": timezone.now(),
            "synced_by": user_key,
        },
    )

    # Create or update linked address
    if has_address:
        if org.address:
            for key, val in address_data.items():
                setattr(org.address, key, val)
            org.address.save()
        else:
            addr, _ = RIRAddress.objects.get_or_create(**address_data)
            org.address = addr
            org.save(update_fields=["address"])

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
    """Sync POC contacts from org poc_links.

    A POC can be linked to the org in several roles (one link per role). The
    role links stay in the org's raw_data; the POC itself is fetched and synced
    once per run, not once per role.
    """
    logs: list[RIRSyncLog] = []
    handles = [handle for handle in dict.fromkeys(link.get("handle") for link in poc_links) if handle]
    log.info(f"Syncing {len(handles)} POC contacts for {org.handle}")

    for handle in handles:
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

        # Build address data from poc_data
        contact_address_data = {
            "street_address": poc_data.get("street_address") or "",
            "city": poc_data.get("city") or "",
            "state_province": poc_data.get("state_province") or "",
            "postal_code": poc_data.get("postal_code") or "",
            "country": poc_data.get("country") or "",
        }
        has_contact_address = any(contact_address_data.values())

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
                "organization": org,
                "raw_data": poc_data.get("raw_data") or {},
                "last_synced": timezone.now(),
                "synced_by": user_key,
            },
        )

        # Create or update linked address
        if has_contact_address:
            if contact.address:
                for key, val in contact_address_data.items():
                    setattr(contact.address, key, val)
                contact.address.save()
            else:
                addr, _ = RIRAddress.objects.get_or_create(**contact_address_data)
                contact.address = addr
                contact.save(update_fields=["address"])

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

    # Build address data from cust_data
    cust_address_data = {
        "street_address": cust_data.get("street_address", ""),
        "city": cust_data.get("city", ""),
        "state_province": cust_data.get("state_province", ""),
        "postal_code": cust_data.get("postal_code", ""),
        "country": cust_data.get("country", ""),
    }
    has_cust_address = any(cust_address_data.values())

    _customer, created = RIRCustomer.objects.update_or_create(
        handle=cust_data["handle"],
        defaults={
            "rir_config": rir_config,
            "customer_name": cust_data.get("customer_name", ""),
            "network": network,
            "raw_data": cust_data,
            "created_date": created_date,
        },
    )

    # Create or update linked address
    if has_cust_address:
        if _customer.address:
            for key, val in cust_address_data.items():
                setattr(_customer.address, key, val)
            _customer.address.save()
        else:
            addr, _ = RIRAddress.objects.get_or_create(**cust_address_data)
            _customer.address = addr
            _customer.save(update_fields=["address"])

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
        sync_log, network = sync_aggregate(backend, rir_config, agg, user_key=user_key, log=log)
        logs.append(sync_log)
        if network:
            agg_nets.append((agg, network))

    return logs, agg_nets


def sync_aggregate(
    backend: ARINBackend,
    rir_config: RIRConfig,
    agg,
    user_key: RIRUserKey | None = None,
    log: logging.Logger = logger,
) -> tuple[RIRSyncLog, RIRNetwork | None]:
    """Link an aggregate to the ARIN net registered to the config's org that covers it.

    Returns (sync_log, network). network is None, and sync_log is a skipped row, unless the
    aggregate belongs to this config's org.
    """
    log.debug(f"Querying ARIN for aggregate {agg.prefix}")
    found = backend.find_net(*prefix_range(agg.prefix))
    net_data = _resolve_owned_net(backend, found, rir_config.org_handle) if found else None
    if net_data is None:
        if found is None:
            handle, message = str(agg.prefix), f"No ARIN network found for {agg.prefix}"
        else:
            owner = found.get("org_handle") or found.get("customer_handle") or "unknown"
            handle = found["handle"]
            message = f"Aggregate {agg.prefix} is not registered to {rir_config.org_handle} (owned by {owner})"
        log.info(message)
        return RIRSyncLog.log_skipped(rir_config, "sync", handle, message), None

    rir_network, created = RIRNetwork.sync_from_arin(
        net_data,
        rir_config,
        aggregate=agg,
        user_key=user_key,
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
    return sync_log, rir_network


def _resolve_owned_net(backend: ARINBackend, net_data: dict, org_handle: str) -> dict | None:
    """Walk up the parent chain from the most specific net to the one registered to org_handle.

    ARIN's mostSpecificNet returns whatever net sits deepest under an address range, which is
    often a customer reassignment beneath our allocation, or a net belonging to another org
    entirely. Only a net registered to the config's own org can anchor the aggregate. A net
    with an org handle never carries a customer handle, so the anchor needs no customer fetch.
    """
    if not org_handle:
        return None
    seen = set()
    while net_data is not None:
        if net_data.get("org_handle") == org_handle:
            return net_data
        seen.add(net_data["handle"])
        parent_handle = net_data.get("parent_net_handle")
        if not parent_handle or parent_handle in seen:
            return None
        net_data = backend.get_network(parent_handle)
    return None


def enqueue_prefix_syncs(
    rir_config: RIRConfig,
    agg_nets: list[tuple],
    user_key: RIRUserKey,
    log: logging.Logger = logger,
) -> None:
    """Queue one prefix discovery job per (aggregate, parent net) pair a config sync returned.

    Each job runs with the key the config sync used and as that key's owner, so its changes are
    logged under the same user as the config sync's: the requesting user for a manual sync, the
    default key's owner for the scheduled sync.
    """
    for agg, parent_net in agg_nets:
        SyncPrefixesJob.enqueue(
            instance=rir_config,
            user=user_key.user,
            aggregate_id=agg.pk,
            parent_handle=parent_net.handle,
            user_key_id=user_key.pk,
        )
        log.info(f"Enqueued prefix sync for aggregate {agg.prefix}")


def sync_config_and_queue_prefixes(
    rir_config: RIRConfig,
    user_key: RIRUserKey,
    log: logging.Logger = logger,
) -> list[RIRSyncLog]:
    """Sync a config with user_key, then queue its per-aggregate prefix discovery.

    Every config sync must be followed by its prefix discovery, so both jobs go through here.
    The caller owns the change log context the sync runs in, which should be user_key's owner so
    the config sync and its prefix jobs are logged under the same user. Returns the sync logs.
    """
    logs, agg_nets = sync_rir_config(rir_config, api_key=user_key.api_key, user_key=user_key, log=log)
    enqueue_prefix_syncs(rir_config, agg_nets, user_key, log=log)
    return logs


class SyncRIRConfigJob(JobRunner):
    """Background job for syncing RIR data."""

    class Meta:
        name = "RIR Sync"

    def run(self, *args, **kwargs):
        from netbox_rir_manager.models import RIRConfig

        rir_config = RIRConfig.objects.get(pk=self.job.object_id)
        user_key = rir_config.resolve_key(self.job.user)
        if not user_key:
            reason = rir_config.no_key_reason(self.job.user)
            self.logger.error(f"{reason}; nothing synced")
            self.job.data = {"rir_config": rir_config.name, "status": "error", "message": reason}
            self.job.save()
            return

        self.job.data = {"rir_config": rir_config.name}
        self.job.save()

        self.logger.info(f"Starting RIR sync for {rir_config.name}")
        with _changelog_context(self.job.user):
            logs = sync_config_and_queue_prefixes(rir_config, user_key, log=self.logger)

        self.job.data["sync_logs_count"] = len(logs)
        self.job.save()
        self.logger.info(f"Sync complete: {len(logs)} log entries")


class SyncPrefixesJob(JobRunner):
    """Discover and sync child prefix reassignments for a single aggregate."""

    class Meta:
        name = "ARIN Prefix Sync"

    def run(self, *args, **kwargs):
        from ipam.models import Aggregate, Prefix

        aggregate_id = kwargs["aggregate_id"]
        parent_handle = kwargs["parent_handle"]

        agg = Aggregate.objects.get(pk=aggregate_id)
        user_key = _queued_user_key(self, kwargs["user_key_id"], "sync", parent_handle)
        if not user_key:
            return
        parent_net = RIRNetwork.objects.get(handle=parent_handle)
        rir_config = parent_net.rir_config
        backend = ARINBackend.from_rir_config(rir_config, api_key=user_key.api_key)

        prefixes = Prefix.objects.filter(prefix__net_contained=agg.prefix)
        self.logger.info(f"Scanning {prefixes.count()} prefixes under {agg.prefix}")

        with _changelog_context(self.job.user):
            for pfx in prefixes:
                self.logger.debug(f"Querying ARIN for prefix {pfx.prefix}")
                pfx_net_data = backend.find_net(*prefix_range(pfx.prefix))
                if pfx_net_data is None:
                    continue

                if pfx_net_data["handle"] == parent_handle:
                    self.logger.debug(f"Prefix {pfx.prefix} returns parent net, skipping")
                    continue

                _net, created = RIRNetwork.sync_from_arin(
                    pfx_net_data,
                    rir_config,
                    prefix=pfx,
                    user_key=user_key,
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
                    backend,
                    rir_config,
                    pfx_net_data,
                    _net,
                    user_key=user_key,
                    log=self.logger,
                )


class ReassignJob(JobRunner):
    """Background job for the automatic reassignment of a prefix at ARIN.

    Queued by the auto_reassign signal, with prefix_id and user_key_id in kwargs. It works out
    the request itself: detailed when the prefix's tenant has a linked RIROrganization, simple
    otherwise, with the customer taken from the tenant and the site's address. Manual
    reassignments do not use this job; they submit what the user entered directly.
    """

    class Meta:
        name = "ARIN Reassign"

    def run(self, *args, **kwargs):
        from ipam.models import Prefix

        from netbox_rir_manager.services.geocoding import SubdivisionCodeError, resolve_site_address
        from netbox_rir_manager.services.reassignment import ReassignmentError, prefix_site, submit_reassignment

        prefix = Prefix.objects.get(pk=kwargs.get("prefix_id"))
        user_key = _queued_user_key(self, kwargs["user_key_id"], "reassign", str(prefix.prefix))
        if not user_key:
            return

        self.job.data = {"prefix": str(prefix.prefix), "status": "starting"}
        self.job.save()
        self.logger.info(f"Starting reassignment for prefix {prefix.prefix}")

        with _changelog_context(self.job.user):
            parent_network = RIRNetwork.auto_reassign_parent_for(prefix)
            if not parent_network:
                message = "No parent allocation opted into auto-reassign on an active config"
                self.logger.error(f"{message} for prefix {prefix.prefix}")
                self.job.data["status"] = "error"
                self.job.data["message"] = message
                self.job.save()
                return

            self.logger.info(f"Found parent network {parent_network.handle}")
            rir_config = parent_network.rir_config
            backend = ARINBackend.from_rir_config(rir_config, api_key=user_key.api_key)

            # Determine reassignment type
            tenant = prefix.tenant
            rir_org = RIROrganization.objects.filter(tenant=tenant).first() if tenant else None

            start_address, end_address = prefix_range(prefix.prefix)

            # Pre-flight: check what ARIN actually has for this range
            self.logger.info(f"Pre-flight: querying ARIN for existing net at {start_address}-{end_address}")
            actual_net = backend.find_net(start_address, end_address)
            if actual_net is not None:
                actual_handle = actual_net.get("handle")

                # Already reassigned at ARIN (different net than parent) -- just sync it
                if actual_handle and actual_handle != parent_network.handle:
                    self.logger.warning(f"Pre-flight: prefix already reassigned as {actual_handle}, syncing instead")
                    RIRNetwork.sync_from_arin(
                        actual_net,
                        rir_config,
                        prefix=prefix,
                        user_key=user_key,
                    )
                    self.job.data["status"] = "synced"
                    self.job.data["message"] = (
                        f"Prefix already has ARIN network {actual_handle} "
                        f"(expected parent {parent_network.handle}). Synced locally."
                    )
                    self.job.save()

                    RIRSyncLog.log_skipped(
                        rir_config,
                        "reassign",
                        actual_handle,
                        f"Prefix {prefix.prefix} already reassigned at ARIN as "
                        f"{actual_handle}. Synced instead of re-reassigning.",
                    )
                    return

            self.logger.info("Pre-flight passed")

            self.logger.info(f"Reassignment type: {'detailed' if rir_org else 'simple'}")

            net = {
                "net_name": build_net_name(tenant.name, prefix.prefix),
                "start_address": start_address,
                "end_address": end_address,
            }
            customer = None
            if rir_org:
                # Detailed reassignment - tenant has a known RIR org
                self.job.data["reassignment_type"] = "detailed"
                self.job.data["org_handle"] = rir_org.handle
                self.job.save()
            else:
                # Simple reassignment - create customer from site address
                self.job.data["reassignment_type"] = "simple"
                self.job.save()

                site = prefix_site(prefix)
                if not site:
                    self.job.data["status"] = "error"
                    self.job.data["message"] = "Prefix has no site"
                    self.job.save()
                    return

                # Resolve site address
                site_address = RIRAddress.get_for_site(site)
                if not site_address:
                    try:
                        site_address = resolve_site_address(site)
                    except SubdivisionCodeError as exc:
                        self._fail_without_customer(rir_config, parent_network, prefix, str(exc))
                        return

                if not site_address:
                    self.job.data["status"] = "error"
                    self.job.data["message"] = "Could not resolve address for site"
                    self.job.save()
                    return

                customer = {"customer_name": tenant.name, **site_address.address_fields()}

            self.logger.info(f"Submitting reassignment to ARIN for {prefix.prefix}")
            try:
                outcome = submit_reassignment(
                    backend,
                    parent_network,
                    user_key,
                    net,
                    customer=customer,
                    org_handle=rir_org.handle if rir_org else None,
                    tenant=tenant,
                    prefix=prefix,
                )
            except ReassignmentError as exc:
                self.logger.error(f"{prefix.prefix}: {exc}")
                self.job.data["status"] = "error"
                self.job.data["message"] = str(exc)
                self.job.save()
                return

            if outcome.recorded:
                self.logger.info(outcome.message)
            else:
                self.logger.error(outcome.message)
            self.job.data["status"] = "success"
            self.job.data["message"] = outcome.message
            if outcome.ticket:
                self.job.data["ticket_number"] = outcome.ticket.ticket_number
            self.job.save()

    def _fail_without_customer(self, rir_config, parent_network, prefix, message):
        """Stop before anything is sent to ARIN because the customer's address is unusable."""
        self.logger.error(f"{prefix.prefix}: {message}")
        RIRSyncLog.objects.create(
            rir_config=rir_config,
            operation="reassign",
            object_type="customer",
            object_handle=parent_network.handle,
            status="error",
            message=f"{prefix.prefix}: {message}",
        )
        self.job.data["status"] = "error"
        self.job.data["message"] = message
        self.job.save()


class RemoveNetworkJob(JobRunner):
    """Background job for removing a reassigned network at ARIN."""

    class Meta:
        name = "ARIN Remove"

    def run(self, *args, **kwargs):
        from netbox_rir_manager.services.arin_results import ARINWriteError
        from netbox_rir_manager.services.net_writes import submit_net_remove

        network = RIRNetwork.objects.get(pk=kwargs.get("network_id"))
        user_key = _queued_user_key(self, kwargs["user_key_id"], "remove", network.handle)
        if not user_key:
            return

        self.job.data = {"network_handle": network.handle, "status": "starting"}
        self.job.save()

        self.logger.info(f"Removing network {network.handle} from ARIN")
        backend = ARINBackend.from_rir_config(network.rir_config, api_key=user_key.api_key)

        with _changelog_context(self.job.user):
            try:
                submit_net_remove(backend, network)
            except ARINWriteError as exc:
                self.logger.error(f"{network.handle}: {exc}")
                self.job.data["status"] = "error"
                self.job.data["message"] = str(exc)
            else:
                self.logger.info(f"Successfully removed network {network.handle}")
                self.job.data["status"] = "success"
        self.job.save()


@system_job(interval=JobIntervalChoices.INTERVAL_DAILY)
class ScheduledRIRSyncJob(JobRunner):
    """Scheduled background job that syncs all active RIR configs."""

    class Meta:
        name = "Scheduled RIR Sync"

    def run(self, *args, **kwargs):
        from netbox_rir_manager.models import RIRConfig

        configs = RIRConfig.objects.filter(is_active=True)
        total_logs = 0
        self.logger.info(f"Starting scheduled sync for {configs.count()} active configs")

        for config in configs:
            self.logger.info(f"Syncing config: {config.name}")

            # No user initiated this run, so only the config's default key may be used.
            user_key = config.resolve_key()
            if not user_key:
                self.logger.warning(f"{config.no_key_reason()}, skipping")
                continue

            self.logger.info(f"Using default key {user_key.pk} for config {config.name}")
            # Log the changes under the key's owner, the account the RIR attributes the calls to.
            try:
                with _changelog_context(user_key.user):
                    total_logs += len(sync_config_and_queue_prefixes(config, user_key, log=self.logger))
            except Exception:
                self.logger.exception(f"Scheduled sync failed for config {config.name}")

        self.logger.info(f"Scheduled sync complete: {configs.count()} configs, {total_logs} logs")
        self.job.data = {"configs_synced": len(configs), "total_logs": total_logs}
        self.job.save()
