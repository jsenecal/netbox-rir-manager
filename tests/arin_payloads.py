"""ARIN write requests and replies shared by the write-path tests."""

from dataclasses import dataclass, field

# The ticket number of the rir_ticket fixture: an ARIN reply carrying it cannot be stored again.
EXISTING_TICKET = "TKT-TEST-001"

DETAILED = {
    "reassignment_type": "detailed",
    "org_handle": "CUST-ARIN",
    "start_address": "192.0.2.0",
    "end_address": "192.0.2.15",
}
REALLOCATION = {"org_handle": "TARGET-ORG", "start_address": "192.0.2.0", "end_address": "192.0.2.15"}


def ticket_result(ticket_number, ticket_type="", **extra):
    """A reply for a write ARIN opened a ticket for."""
    return {
        "ticket_number": ticket_number,
        "ticket_type": ticket_type,
        "ticket_status": "PENDING_REVIEW",
        "raw_data": {},
        **extra,
    }


def immediate_result(child_handle=None):
    """A reply for a write ARIN processed immediately: no ticket, and the new child net if any."""
    return {"net": {"handle": child_handle, "net_name": "CHILD-NET"}} if child_handle else {}


@dataclass(frozen=True)
class WriteFailure:
    """A write ARIN refuses: the backend method and what it returns, and what the user and log see."""

    method: str
    detail: str
    log: tuple  # (operation, sync log message)
    data: dict = field(default_factory=dict)
    returns: object = None


WRITE_FAILURES = {
    "reassign": WriteFailure(
        "reassign_network", "Reassignment failed at ARIN.", ("reassign", "Reassignment of 192.0.2.0 failed"), DETAILED
    ),
    "reallocate": WriteFailure(
        "reallocate_network", "Reallocation failed at ARIN.", ("reallocate", "Reallocation failed"), REALLOCATION
    ),
    "delete": WriteFailure(
        "delete_network", "Failed to delete network at ARIN.", ("delete", "Failed to delete network at ARIN")
    ),
    "remove": WriteFailure(
        "remove_network",
        "Failed to remove network from ARIN.",
        ("remove", "Failed to remove network from ARIN"),
        returns=False,
    ),
}
