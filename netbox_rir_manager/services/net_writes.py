"""Reallocating, removing and deleting nets at ARIN, shared by the UI, the API and the jobs."""

from netbox_rir_manager.services.arin_results import ARINWriteError, net_request, record_arin_result, sync_log


def reallocation_request(data):
    """Pull the net to reallocate (recipient org handle, name, range) out of validated data."""
    return {"org_handle": data["org_handle"], **net_request(data)}


def submit_reallocation(backend, parent, user_key, net):
    """Reallocate part of parent to another org at ARIN and record the outcome.

    net comes from reallocation_request. Returns the ARINOutcome of record_arin_result, or
    raises ARINWriteError after logging the failure.
    """
    result = backend.reallocate_network(parent.handle, net)
    if result is None:
        sync_log(parent.rir_config, "reallocate", "network", parent.handle, "error", "Reallocation failed")
        raise ARINWriteError("Reallocation failed at ARIN.")
    return record_arin_result(
        result,
        network=parent,
        user_key=user_key,
        operation="reallocate",
        action="Reallocation",
        ticket_type="IPV4_REALLOCATE",
    )


def submit_net_delete(backend, network, user_key):
    """Delete network at ARIN and record the outcome.

    Returns the ARINOutcome of record_arin_result, or raises ARINWriteError after logging the
    failure.
    """
    result = backend.delete_network(network.handle)
    if result is None:
        message = "Failed to delete network at ARIN"
        sync_log(network.rir_config, "delete", "network", network.handle, "error", message)
        raise ARINWriteError(f"{message}.")
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

    Raises ARINWriteError after logging a failure.
    """
    if not backend.remove_network(network.handle):
        message = "Failed to remove network from ARIN"
        sync_log(network.rir_config, "remove", "network", network.handle, "error", message)
        raise ARINWriteError(f"{message}.")
    sync_log(
        network.rir_config,
        "remove",
        "network",
        network.handle,
        "success",
        f"Removed network {network.handle} from ARIN",
    )
