from utilities.choices import ChoiceSet


class SyncOperationChoices(ChoiceSet):
    key = "RIRSyncLog.operation"

    CHOICES = [
        ("sync", "Sync", "blue"),
        ("create", "Create", "green"),
        ("update", "Update", "yellow"),
        ("delete", "Delete", "red"),
        ("reassign", "Reassign", "purple"),
        ("reallocate", "Reallocate", "indigo"),
        ("remove", "Remove", "orange"),
    ]


class SyncStatusChoices(ChoiceSet):
    key = "RIRSyncLog.status"

    CHOICES = [
        ("success", "Success", "green"),
        ("error", "Error", "red"),
        ("skipped", "Skipped", "gray"),
    ]


class ContactTypeChoices(ChoiceSet):
    key = "RIRContact.contact_type"

    CHOICES = [
        ("PERSON", "Person", "blue"),
        ("ROLE", "Role", "purple"),
    ]


class TicketStatusChoices(ChoiceSet):
    key = "RIRTicket.status"

    CHOICES = [
        ("pending_confirmation", "Pending Confirmation", "cyan"),
        ("pending_review", "Pending Review", "blue"),
        ("assigned", "Assigned", "indigo"),
        ("in_progress", "In Progress", "yellow"),
        ("resolved", "Resolved", "green"),
        ("closed", "Closed", "gray"),
        ("approved", "Approved", "teal"),
    ]


class TicketResolutionChoices(ChoiceSet):
    key = "RIRTicket.resolution"

    CHOICES = [
        ("accepted", "Accepted", "green"),
        ("denied", "Denied", "red"),
        ("abandoned", "Abandoned", "gray"),
        ("processed", "Processed", "blue"),
        ("withdrawn", "Withdrawn", "orange"),
        ("other", "Other", "gray"),
    ]


class TicketTypeChoices(ChoiceSet):
    key = "RIRTicket.ticket_type"

    CHOICES = [
        ("IPV4_SIMPLE_REASSIGN", "IPv4 Simple Reassign", "blue"),
        ("IPV4_DETAILED_REASSIGN", "IPv4 Detailed Reassign", "indigo"),
        ("IPV4_REALLOCATE", "IPv4 Reallocate", "purple"),
        ("IPV6_DETAILED_REASSIGN", "IPv6 Detailed Reassign", "indigo"),
        ("IPV6_REALLOCATE", "IPv6 Reallocate", "purple"),
        ("NET_DELETE_REQUEST", "NET Delete Request", "red"),
    ]


def normalize_ticket_status(arin_status: str) -> str:
    """Map ARIN ticket status strings to TicketStatusChoices values."""
    mapping = {
        "PENDING_CONFIRMATION": "pending_confirmation",
        "PENDING_REVIEW": "pending_review",
        "ASSIGNED": "assigned",
        "IN_PROGRESS": "in_progress",
        "RESOLVED": "resolved",
        "CLOSED": "closed",
        "APPROVED": "approved",
    }
    return mapping.get(arin_status, "pending_review")
