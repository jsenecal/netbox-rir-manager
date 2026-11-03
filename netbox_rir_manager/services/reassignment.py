"""Submitting a reassignment to ARIN, shared by the UI, the API and the automatic reassign job."""

from django.utils import timezone

from netbox_rir_manager.models import RIRAddress, RIRCustomer
from netbox_rir_manager.services.arin_results import ARINWriteError, net_request, record_arin_result, sync_log

CUSTOMER_FIELDS = ("customer_name", *RIRAddress.ADDRESS_FIELDS)


class ReassignmentError(ARINWriteError):
    """ARIN refused or failed a step of the reassignment; the message is safe to show a user."""


def reassignment_request(data):
    """Pull a reassignment request out of validated form or serializer data.

    Returns (net, customer, org_handle) for submit_reassignment: a simple reassignment
    carries the customer's details, a detailed one the recipient org handle.
    """
    net = net_request(data)
    if data["reassignment_type"] == "simple":
        return net, {field: data.get(field) or "" for field in CUSTOMER_FIELDS}, None
    return net, None, data["org_handle"]


def prefix_site(prefix):
    """The Site a prefix is scoped to, or None.

    Prefix.site is not that site: it is a reverse generic relation, so it returns a related
    manager (always truthy). The scope's site is cached on _site; fall back to the scope itself.
    """
    from dcim.models import Site

    site = getattr(prefix, "_site", None)
    if site is None and isinstance(getattr(prefix, "scope", None), Site):
        site = prefix.scope
    return site


def submit_reassignment(backend, parent, user_key, net, *, customer=None, org_handle=None, tenant=None, prefix=None):
    """Reassign part of parent at ARIN and record the outcome.

    net holds net_name, start_address and end_address. Pass customer (a dict of
    CUSTOMER_FIELDS) for a simple reassignment, which first creates the customer at ARIN,
    or org_handle for a detailed one. The child net ARIN returns is linked to prefix.

    Returns the ARINOutcome of record_arin_result (its ticket is None when ARIN processed the
    reassignment immediately), or raises ReassignmentError after logging the failure.
    """
    rir_config = parent.rir_config
    net_data = dict(net)

    if customer is not None:
        customer_result = backend.create_customer(parent.handle, customer)
        if customer_result is None:
            sync_log(
                rir_config,
                "create",
                "customer",
                parent.handle,
                "error",
                f"Failed to create customer for {net['start_address']}",
            )
            raise ReassignmentError("Failed to create customer at ARIN.")
        address, _ = RIRAddress.objects.get_or_create(**{f: customer[f] for f in RIRAddress.ADDRESS_FIELDS})
        RIRCustomer.objects.create(
            rir_config=rir_config,
            handle=customer_result["handle"],
            customer_name=customer["customer_name"],
            address=address,
            network=parent,
            tenant=tenant,
            raw_data=customer_result,
            created_date=timezone.now(),
        )
        net_data["customer_handle"] = customer_result["handle"]
    else:
        net_data["org_handle"] = org_handle

    result = backend.reassign_network(parent.handle, net_data)
    if result is None:
        sync_log(
            rir_config, "reassign", "network", parent.handle, "error", f"Reassignment of {net['start_address']} failed"
        )
        raise ReassignmentError("Reassignment failed at ARIN.")

    return record_arin_result(
        result,
        network=parent,
        user_key=user_key,
        operation="reassign",
        action="Reassignment",
        ticket_type="IPV4_SIMPLE_REASSIGN",
        link_net=True,
        prefix=prefix,
    )
