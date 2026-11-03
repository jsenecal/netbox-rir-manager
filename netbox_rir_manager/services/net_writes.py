"""Reallocating, removing and deleting nets at ARIN, shared by the UI, the API and the jobs."""

from netbox_rir_manager.models import RIRSyncLog
from netbox_rir_manager.services.arin_results import arin_write, net_request, record_arin_result


def reallocation_request(data):
    """Pull the net to reallocate (recipient org handle, name, range) out of validated data."""
    return {"org_handle": data["org_handle"], **net_request(data)}


def submit_reallocation(backend, parent, user_key, net):
    """Reallocate part of parent to another org at ARIN and record the outcome.

    net comes from reallocation_request. The child net ARIN returns is synced and linked, as
    for a reassignment. Returns the ARINOutcome of record_arin_result, or raises
    ARINWriteError after logging the failure, with ARIN's reason when it refused
    (ARINDataError when the request's own data cannot be sent to ARIN).
    """
    result = arin_write(
        lambda: backend.reallocate_network(parent.handle, net),
        parent.rir_config,
        "reallocate",
        "network",
        parent.handle,
        f"Reallocation of {net['start_address']} failed at ARIN",
    )
    return record_arin_result(
        result,
        network=parent,
        user_key=user_key,
        operation="reallocate",
        action="Reallocation",
        ticket_type="IPV4_REALLOCATE",
        link_net=True,
    )


def submit_net_delete(backend, network, user_key):
    """Delete network at ARIN and record the outcome.

    Returns the ARINOutcome of record_arin_result, or raises ARINWriteError after logging the
    failure, with ARIN's reason when it refused.
    """
    result = arin_write(
        lambda: backend.delete_network(network.handle),
        network.rir_config,
        "delete",
        "network",
        network.handle,
        "Failed to delete network at ARIN",
    )
    return record_arin_result(
        result,
        network=network,
        user_key=user_key,
        operation="delete",
        action="Delete request",
        ticket_type="NET_DELETE_REQUEST",
    )


def submit_net_remove(backend, network):
    """Remove a reassigned or reallocated network at ARIN and log the outcome.

    Raises ARINWriteError after logging a failure, with ARIN's reason when it refused.
    """
    arin_write(
        lambda: backend.remove_network(network.handle),
        network.rir_config,
        "remove",
        "network",
        network.handle,
        "Failed to remove network from ARIN",
    )
    RIRSyncLog.record(
        network.rir_config,
        "remove",
        "network",
        network.handle,
        "success",
        f"Removed network {network.handle} from ARIN",
    )
