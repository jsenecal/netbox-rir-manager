"""Recording, in NetBox, the outcome of a write sent to ARIN."""

import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from netbox_rir_manager.backends.base import RIRDataError, RIRRequestError
from netbox_rir_manager.choices import normalize_ticket_status
from netbox_rir_manager.models import RIRNetwork, RIRSyncLog, RIRTicket

logger = logging.getLogger(__name__)


class ARINWriteError(Exception):
    """ARIN refused or failed a write; the message is safe to show a user."""


class ARINDataError(ARINWriteError):
    """The request's own data cannot be sent to ARIN, so nothing was submitted."""


@dataclass
class ARINOutcome:
    """What NetBox recorded about a write ARIN accepted.

    ticket is None when ARIN processed the write immediately, or when recording failed
    (recorded is False). net is the child network linked from ARIN's reply, if any.
    message describes the outcome and is safe to show a user.
    """

    message: str
    ticket: RIRTicket | None = None
    net: RIRNetwork | None = None
    recorded: bool = True


def net_request(data):
    """The net name and address range of a reassignment or reallocation, from validated data."""
    return {
        "net_name": data.get("net_name") or "",
        "start_address": str(data["start_address"]),
        "end_address": str(data["end_address"]),
    }


def record_arin_result(result, *, network, user_key, operation, action, ticket_type, link_net=False, prefix=None):
    """Record a write ARIN accepted for network: a ticket if ARIN opened one, and a sync log.

    ARIN processes some writes (NET deletes, simple reassignments) immediately and opens no
    ticket. Those get no RIRTicket -- the ticket number is unique and there is none to store --
    only a success sync log. With link_net, the child net in ARIN's reply is synced and linked
    to prefix.

    The change has already happened at ARIN when this runs, so a failure to record it is
    logged and returned (recorded=False) rather than raised: the caller must never report a
    change ARIN made as failed.

    action is a capitalised noun for messages ("Reassignment"); ticket_type is the fallback
    when ARIN's reply does not name one.
    """
    rir_config = network.rir_config
    ticket_number = result.get("ticket_number") or ""
    if ticket_number:
        message = f"{action} submitted, ticket {ticket_number}."
    else:
        message = f"{action} processed immediately by ARIN; no ticket was opened."

    try:
        with transaction.atomic():
            ticket = None
            if ticket_number:
                ticket = RIRTicket.objects.create(
                    rir_config=rir_config,
                    ticket_number=ticket_number,
                    ticket_type=result.get("ticket_type") or ticket_type,
                    status=normalize_ticket_status(result.get("ticket_status", "")),
                    network=network,
                    submitted_by=user_key,
                    created_date=timezone.now(),
                    raw_data=result.get("raw_data", {}),
                )
            net = None
            child = result.get("net")
            if link_net and child and child.get("handle"):
                net, _ = RIRNetwork.sync_from_arin(child, rir_config, prefix=prefix, user_key=user_key)
            sync_log(rir_config, operation, "network", network.handle, "success", message)
    except Exception as exc:
        # Anything raised here would turn an ARIN change that happened into an error response.
        logger.exception("%s of %s succeeded at ARIN but could not be recorded", action, network.handle)
        failure = f"{action} succeeded at ARIN"
        if ticket_number:
            failure += f" (ticket {ticket_number})"
        failure += ", but NetBox could not record it."
        # Database errors span several lines; keep the message on one.
        error = " ".join(str(exc).split())
        try:
            with transaction.atomic():
                sync_log(rir_config, operation, "network", network.handle, "error", f"{failure} Error: {error}")
        except Exception:
            logger.exception("Could not write the sync log for %s of %s", action, network.handle)
        return ARINOutcome(message=f"{failure} Check the NetBox log. Error: {error}", recorded=False)

    return ARINOutcome(message=message, ticket=ticket, net=net)


def sync_log(rir_config, operation, object_type, handle, status, message):
    """Write an RIRSyncLog row."""
    return RIRSyncLog.objects.create(
        rir_config=rir_config,
        operation=operation,
        object_type=object_type,
        object_handle=handle,
        status=status,
        message=message,
    )


def data_error(rir_config, operation, object_type, handle, exc, error_cls=ARINDataError):
    """Log a request-data problem the backend reported (RIRDataError) and wrap it for the caller."""
    sync_log(rir_config, operation, object_type, handle, "error", str(exc))
    return error_cls(str(exc))


def arin_write(
    call,
    rir_config,
    operation,
    object_type,
    handle,
    message,
    *,
    log=None,
    error_cls=ARINWriteError,
    data_error_cls=ARINDataError,
):
    """Run a backend write, call(), and return its result; log and raise if it did not succeed.

    message is the user's message without its final period ("Reallocation failed at ARIN"); log
    is the sync log's wording, message by default. ARIN's reason, when it refused the write
    (RIRRequestError), is appended to both; a result of None or False means ARIN could not be
    reached. Data the backend cannot send (RIRDataError) raises data_error_cls instead.
    """
    try:
        result = call()
    except RIRDataError as exc:
        raise data_error(rir_config, operation, object_type, handle, exc, data_error_cls) from exc
    except RIRRequestError as exc:
        raise _write_failure(rir_config, operation, object_type, handle, message, log, error_cls, exc) from exc
    if result is None or result is False:
        raise _write_failure(rir_config, operation, object_type, handle, message, log, error_cls)
    return result


def _write_failure(rir_config, operation, object_type, handle, message, log, error_cls, refusal=None):
    detail = f": {refusal}" if refusal else ""
    sync_log(rir_config, operation, object_type, handle, "error", f"{log or message}{detail}")
    return error_cls(f"{message}{detail or '.'}")
