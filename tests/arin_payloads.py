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


# Error payloads ARIN's OT&E environment returned, verbatim.
_ERROR_XML = (
    '<error xmlns="http://www.arin.net/regrws/core/v1"><message>{message}</message><code>{code}</code>'
    "<components>{components}</components><additionalInfo/></error>"
)
_COMPONENT_XML = "<component><name>{}</name><message>{}</message></component>"


def _error_xml(code, message, *components):
    return _ERROR_XML.format(
        code=code, message=message, components="".join(_COMPONENT_XML.format(*c) for c in components)
    )


ARIN_ERRORS = {
    # A customer with country XX.
    "bad_country": _error_xml(
        "E_BAD_REQUEST",
        "This method requires certain parameters.  Please see the documentation for details.",
        ("iso3166-1", "A valid country code is required."),
    ),
    # A reassignment overlapping an existing net.
    "overlap": _error_xml(
        "E_ENTITY_VALIDATION",
        "Payload entity failed to validate; see component messages for details.",
        ("startAddress", "IP range overlaps with existing network(s)."),
    ),
    # A Canadian customer with no province and an empty postal code.
    "two_components": _error_xml(
        "E_ENTITY_VALIDATION",
        "Payload entity failed to validate; see component messages for details.",
        ("postalCode", "Postal code not in the correct format for country selected."),
        ("iso3166-2", "Value is required if the country selected is US or Canada."),
    ),
    # Looking up a net handle that does not exist.
    "not_found": _error_xml(
        "E_OBJECT_NOT_FOUND",
        "The referenced object does not exist.",
        ("handle", "The referenced object does not exist."),
    ),
    # Any call with a bad API key.
    "authentication": _error_xml("E_AUTHENTICATION", "The API key specified was missing or invalid."),
}

BAD_COUNTRY = "iso3166-1: A valid country code is required."
OVERLAP = "startAddress: IP range overlaps with existing network(s)."
NOT_FOUND = "handle: The referenced object does not exist."


def arin_error(name):
    """The pyregrws Error for one of ARIN_ERRORS."""
    from regrws.models import Error

    return Error.from_xml(ARIN_ERRORS[name].encode())


@dataclass(frozen=True)
class WriteFailure:
    """A write ARIN fails or refuses: the backend method, and what the user and log see.

    returns is what the backend method returns when ARIN cannot be reached, giving detail and
    log. refusal is ARIN's reason when it refuses the write, given in refused_detail and
    refused_log.
    """

    method: str
    detail: str
    log: tuple  # (operation, sync log message)
    refusal: str
    refused_detail: str
    refused_log: str
    data: dict = field(default_factory=dict)
    returns: object = None

    def arrange(self, backend, refused):
        """Make backend's write method fail (refused, or ARIN unreachable); return the expected (detail, log)."""
        from netbox_rir_manager.backends.base import RIRRequestError

        method = getattr(backend, self.method)
        if refused:
            method.side_effect = RIRRequestError(self.refusal)
            return self.refused_detail, (self.log[0], self.refused_log)
        method.return_value = self.returns
        return self.detail, self.log


WRITE_FAILURES = {
    "reassign": WriteFailure(
        "reassign_network",
        "Reassignment failed at ARIN.",
        ("reassign", "Reassignment of 192.0.2.0 failed"),
        OVERLAP,
        f"Reassignment failed at ARIN: {OVERLAP}",
        f"Reassignment of 192.0.2.0 failed: {OVERLAP}",
        DETAILED,
    ),
    "reallocate": WriteFailure(
        "reallocate_network",
        "Reallocation failed at ARIN.",
        ("reallocate", "Reallocation failed"),
        OVERLAP,
        f"Reallocation failed at ARIN: {OVERLAP}",
        f"Reallocation failed: {OVERLAP}",
        REALLOCATION,
    ),
    "delete": WriteFailure(
        "delete_network",
        "Failed to delete network at ARIN.",
        ("delete", "Failed to delete network at ARIN"),
        NOT_FOUND,
        f"Failed to delete network at ARIN: {NOT_FOUND}",
        f"Failed to delete network at ARIN: {NOT_FOUND}",
    ),
    "remove": WriteFailure(
        "remove_network",
        "Failed to remove network from ARIN.",
        ("remove", "Failed to remove network from ARIN"),
        NOT_FOUND,
        f"Failed to remove network from ARIN: {NOT_FOUND}",
        f"Failed to remove network from ARIN: {NOT_FOUND}",
        returns=False,
    ),
}
