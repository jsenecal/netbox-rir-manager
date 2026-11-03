"""Submitting a reassignment to ARIN, shared by the UI, the API and the automatic reassign job."""

from django.utils import timezone

from netbox_rir_manager.backends.base import RIRDataError
from netbox_rir_manager.models import RIRAddress, RIRCustomer
from netbox_rir_manager.services.arin_results import (
    ARINDataError,
    ARINWriteError,
    arin_write,
    data_error,
    net_request,
    record_arin_result,
)

CUSTOMER_FIELDS = ("customer_name", *RIRAddress.ADDRESS_FIELDS)


class ReassignmentError(ARINWriteError):
    """ARIN refused or failed a step of the reassignment; the message is safe to show a user."""


class ReassignmentDataError(ReassignmentError, ARINDataError):
    """Reassignment data that cannot be sent to ARIN.

    A ReassignmentError so the existing UI and job handlers catch it, and an ARINDataError so
    the API answers 400.
    """


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
    reassignment immediately), or raises ReassignmentError after logging the failure, with
    ARIN's reason when it refused (ReassignmentDataError when the request's own data cannot be
    sent to ARIN).
    """
    rir_config = parent.rir_config
    net_data = dict(net)
    if customer is None:
        net_data["org_handle"] = org_handle

    # Validate the net first so a refused net never leaves a customer behind at ARIN.
    try:
        backend.validate_reassignment(net_data)
    except RIRDataError as exc:
        raise data_error(rir_config, "reassign", "network", parent.handle, exc, ReassignmentDataError) from exc

    if customer is not None:
        customer_result = arin_write(
            lambda: backend.create_customer(parent.handle, customer),
            rir_config,
            "create",
            "customer",
            parent.handle,
            "Failed to create customer at ARIN",
            log=f"Failed to create customer for {net['start_address']}",
            error_cls=ReassignmentError,
            data_error_cls=ReassignmentDataError,
        )
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

    result = arin_write(
        lambda: backend.reassign_network(parent.handle, net_data),
        rir_config,
        "reassign",
        "network",
        parent.handle,
        "Reassignment failed at ARIN",
        log=f"Reassignment of {net['start_address']} failed",
        error_cls=ReassignmentError,
        data_error_cls=ReassignmentDataError,
    )

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
