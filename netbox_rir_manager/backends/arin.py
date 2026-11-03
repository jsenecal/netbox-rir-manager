from __future__ import annotations

import logging
from ipaddress import ip_address
from typing import TYPE_CHECKING, Any

import pycountry
from pydantic import ValidationError
from regrws.api.core import Api
from regrws.models import Customer, Error, Net
from tenacity import RetryError, Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from netbox_rir_manager.backends import register_backend
from netbox_rir_manager.backends.base import RIRBackend, RIRDataError, RIRRequestError
from netbox_rir_manager.net_names import to_ascii

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from netbox_rir_manager.models import RIRConfig


def error_detail(error: Error) -> str:
    """ARIN's reason for an Error, on one line.

    The components name each problem ("iso3166-1: A valid country code is required."), so they
    replace ARIN's generic message when present.
    """
    parts = [f"{c.name}: {c.message}" for c in error.components] or [error.message]
    return " ".join([*parts, *error.additional_info])


def _data_error(model_cls, *problems) -> RIRDataError:
    """An RIRDataError for data pyregrws' model_cls cannot take.

    Each problem is (loc, msg): loc is the field path as a tuple, empty for the whole model.
    """
    text = "; ".join(f"{'.'.join(map(str, loc))}: {msg}" if loc else msg for loc, msg in problems)
    return RIRDataError(f"Invalid {model_cls.__name__} details for ARIN: {text}")


@register_backend
class ARINBackend(RIRBackend):
    """ARIN Reg-RWS backend using pyregrws."""

    name = "ARIN"

    def __init__(self, api_key: str, base_url: str | None = None):
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.api = Api(**kwargs)

    @classmethod
    def from_rir_config(cls, rir_config: RIRConfig, api_key: str) -> ARINBackend:
        """Create backend instance from an RIRConfig model."""
        return cls(
            api_key=api_key,
            base_url=rir_config.api_url or None,
        )

    def _call_with_retry(self, func, *args, **kwargs):
        from django.conf import settings as django_settings

        plugin_config = django_settings.PLUGINS_CONFIG.get("netbox_rir_manager", {})
        max_attempts = plugin_config.get("api_retry_count", 3)
        backoff = plugin_config.get("api_retry_backoff", 2)

        try:
            for attempt in Retrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, max=backoff * max_attempts),
                retry=retry_if_exception_type((ConnectionError, OSError, TimeoutError)),
            ):
                with attempt:
                    return func(*args, **kwargs)
        except RetryError:
            return None

    def _write_call(self, func, *args, **kwargs):
        """_call_with_retry for a write path.

        Returns None if ARIN cannot be reached, and raises RIRRequestError when ARIN refuses the
        request, including a lookup it answers with an error such as E_OBJECT_NOT_FOUND.
        """
        result = self._call_with_retry(func, *args, **kwargs)
        if isinstance(result, Error):
            raise RIRRequestError(error_detail(result))
        return result

    def authenticate(self, rir_config: RIRConfig) -> bool:
        if not rir_config.org_handle:
            return False
        result = self._call_with_retry(self.api.org.from_handle, rir_config.org_handle)
        return not (result is None or isinstance(result, Error))

    def get_organization(self, handle: str) -> dict[str, Any] | None:
        result = self._call_with_retry(self.api.org.from_handle, handle)
        if result is None or isinstance(result, Error):
            return None
        return self._org_to_dict(result)

    def get_network(self, handle: str) -> dict[str, Any] | None:
        result = self._call_with_retry(self.api.net.from_handle, handle)
        if result is None or isinstance(result, Error):
            return None
        return self._net_to_dict(result)

    def get_poc(self, handle: str) -> dict[str, Any] | None:
        result = self._call_with_retry(self.api.poc.from_handle, handle)
        if result is None or isinstance(result, Error):
            return None
        return self._poc_to_dict(result)

    def find_net(self, start_address: str, end_address: str) -> dict[str, Any] | None:
        """Find a network by start/end address range."""
        result = self._call_with_retry(self.api.net.find_net, start_address, end_address)
        if result is None or isinstance(result, Error):
            return None
        return self._net_to_dict(result)

    def get_asn(self, asn: int) -> dict[str, Any] | None:
        return None

    def sync_resources(self, rir_config: RIRConfig, resource_type: str | None = None) -> list[dict[str, Any]]:
        return []

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def update_network(self, handle: str, data: dict[str, Any]) -> dict[str, Any] | None:
        net = self._write_call(self.api.net.from_handle, handle)
        if net is None:
            return None
        if "net_name" in data:
            net.net_name = data["net_name"]
        result = self._write_call(net.save)
        if result is None:
            return None
        return self._net_to_dict(result)

    def reassign_network(self, parent_handle: str, net_data: dict[str, Any]) -> dict[str, Any] | None:
        return self._write_child_net(parent_handle, net_data, "S", self.api.net.reassign)

    def reallocate_network(self, parent_handle: str, net_data: dict[str, Any]) -> dict[str, Any] | None:
        return self._write_child_net(parent_handle, net_data, "A", self.api.net.reallocate)

    def _write_child_net(self, parent_handle: str, net_data: dict[str, Any], block_type: str, submit):
        """Build the child net (raising RIRDataError before any call), then submit it under the parent."""
        child_net = self._build_net(net_data, block_type, parent_handle)
        parent = self._write_call(self.api.net.from_handle, parent_handle)
        if parent is None:
            return None
        result = self._write_call(submit, parent, child_net)
        if result is None:
            return None
        return self._ticket_request_to_dict(result)

    def remove_network(self, handle: str) -> bool:
        net = self._write_call(self.api.net.from_handle, handle)
        if net is None:
            return False
        return self._write_call(self.api.net.remove, net) is not None

    def delete_network(self, handle: str) -> dict[str, Any] | None:
        net = self._write_call(self.api.net.from_handle, handle)
        if net is None:
            return None
        result = self._write_call(net.delete)
        if result is None:
            return None
        return self._ticket_request_to_dict(result)

    def get_customer(self, handle: str) -> dict[str, Any] | None:
        result = self._call_with_retry(self.api.customer.from_handle, handle)
        if result is None or isinstance(result, Error):
            return None
        return self._customer_to_dict(result)

    def create_customer(self, parent_net_handle: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """Create a recipient customer under the parent net.

        Raises RIRDataError when the customer details cannot form a valid Reg-RWS payload,
        before anything is sent to ARIN, and RIRRequestError when ARIN refuses the request
        (the parent net lookup or the customer).
        """
        payload = self._customer_payload(data)
        parent = self._write_call(self.api.net.from_handle, parent_net_handle)
        if parent is None:
            return None
        result = self._write_call(self.api.customer.create_for_net, parent, **payload)
        if result is None:
            return None
        return self._customer_to_dict(result)

    def validate_reassignment(self, net_data: dict[str, Any]) -> None:
        """Raise RIRDataError if reassign_network would refuse net_data, without contacting ARIN."""
        if not (net_data.get("customer_handle") or net_data.get("org_handle")):
            # A simple reassignment's customer handle only exists after create_customer.
            net_data = {**net_data, "customer_handle": "C-PENDING"}
        self._build_net(net_data, "S")

    @classmethod
    def _build_net(cls, net_data: dict[str, Any], block_type: str, parent_handle: str | None = None) -> Net:
        """Build the child Net from the plugin's flat net data.

        The range goes in a single net block typed S for a reassignment or A for a
        reallocation, and the IP version comes from its start address. ARIN refuses a
        reassignment or reallocation whose parentNetHandle does not match the parent in the
        request URL, so the parent's handle is carried in the payload.
        """
        start = net_data.get("start_address")
        try:
            version = ip_address(start).version
        except ValueError as exc:
            raise _data_error(Net, (("start_address",), exc)) from exc
        payload = {
            "version": version,
            "net_name": net_data.get("net_name") or None,
            "customer_handle": net_data.get("customer_handle") or None,
            "org_handle": net_data.get("org_handle") or None,
            "parent_net_handle": parent_handle,
            "net_blocks": [{"type": block_type, "start_address": start, "end_address": net_data.get("end_address")}],
        }
        return cls._build_model(Net, payload)

    @staticmethod
    def _build_model(model_cls, data: dict[str, Any]):
        """Build a pyregrws model, raising RIRDataError with a readable message if it refuses the data."""
        try:
            return model_cls(**data)
        except ValidationError as exc:
            raise _data_error(model_cls, *((err["loc"], err["msg"]) for err in exc.errors())) from exc

    @classmethod
    def _customer_payload(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Map the plugin's flat customer dict to pyregrws Customer keyword arguments.

        Reg-RWS payloads are ASCII-only (only comments may carry accented letters), so the
        free-text fields are transliterated. Empty optional fields become None, which pyregrws
        omits from the XML. pyregrws only checks the country code's length, so it is also
        looked up in ISO 3166-1, which ARIN requires. The lookup must follow the model build:
        pyregrws refuses a missing code there, and pycountry raises LookupError for None.
        """
        lines = [to_ascii(line).strip() for line in (data.get("street_address") or "").splitlines()]
        payload = {
            "customer_name": to_ascii(data.get("customer_name") or "").strip(),
            "iso3166_1": {"code2": data.get("country") or None},
            "street_address": [{"number": n, "line": line} for n, line in enumerate(filter(None, lines), start=1)],
            "city": to_ascii(data.get("city") or "").strip(),
            "iso3166_2": data.get("state_province") or None,
            "postal_code": to_ascii(data.get("postal_code") or "").strip() or None,
        }
        customer = cls._build_model(Customer, payload)
        country = customer.iso3166_1.code2
        if pycountry.countries.get(alpha_2=country) is None:
            raise _data_error(
                Customer, (("iso3166_1", "code2"), f"{country} is not an ISO 3166-1 alpha-2 country code")
            )
        return payload

    # ------------------------------------------------------------------
    # Internal helpers to normalise pyregrws models to plain dicts
    #
    # Each method starts from _safe_serialize (the full pydantic .dict()
    # round-tripped through JSON) and then flattens/normalises nested
    # structures.  This means new fields added to pyregrws are
    # automatically present in the dict without manual mapping.
    # ------------------------------------------------------------------

    @staticmethod
    def _flatten_street(lines: list | None) -> str:
        if not lines:
            return ""
        return "\n".join(entry.get("line", "") for entry in lines if entry.get("line"))

    @staticmethod
    def _flatten_phone(phones: list | None) -> str:
        if not phones:
            return ""
        p = phones[0]
        if isinstance(p, str):
            return p
        number = p.get("number", "") or ""
        extension = p.get("extension") or ""
        return f"{number}x{extension}" if extension else number

    @staticmethod
    def _flatten_email(emails: list | None) -> str:
        if not emails:
            return ""
        return str(emails[0])

    @staticmethod
    def _flatten_country(iso3166_1: dict | None) -> str:
        if not iso3166_1:
            return ""
        return iso3166_1.get("code2", "") or ""

    def _poc_to_dict(self, poc: Any) -> dict[str, Any]:
        data = self._safe_serialize(poc)
        data["email"] = self._flatten_email(data.get("emails"))
        data["phone"] = self._flatten_phone(data.get("phones"))
        data["street_address"] = self._flatten_street(data.get("street_address"))
        data["state_province"] = data.get("iso3166_2", "") or ""
        data["country"] = self._flatten_country(data.get("iso3166_1"))
        data["raw_data"] = data.copy()
        return data

    def _org_to_dict(self, org: Any) -> dict[str, Any]:
        data = self._safe_serialize(org)
        data["name"] = data.get("org_name", "") or ""
        data["street_address"] = self._flatten_street(data.get("street_address"))
        data["state_province"] = data.get("iso3166_2", "") or ""
        data["country"] = self._flatten_country(data.get("iso3166_1"))
        data["raw_data"] = data.copy()
        return data

    def _net_to_dict(self, net: Any) -> dict[str, Any]:
        data = self._safe_serialize(net)
        # Extract net_type from the first net block's description
        net_blocks = data.get("net_blocks") or []
        data["net_type"] = net_blocks[0].get("description", "") if net_blocks else ""
        data["raw_data"] = data.copy()
        return data

    def _ticket_request_to_dict(self, ticket_request: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        ticket = getattr(ticket_request, "ticket", None)
        if ticket:
            ticket_data = self._safe_serialize(ticket)
            result["ticket_number"] = ticket_data.get("ticket_no", "")
            result["ticket_status"] = ticket_data.get("web_ticket_status", "")
            result["ticket_type"] = ticket_data.get("web_ticket_type", "")
            result["ticket_resolution"] = ticket_data.get("web_ticket_resolution", "")
            result["created_date"] = ticket_data.get("created_date", "")
            result["resolved_date"] = ticket_data.get("resolved_date", "")
            result["raw_data"] = ticket_data
        net = getattr(ticket_request, "net", None)
        if net:
            result["net"] = self._net_to_dict(net)
        return result

    def _customer_to_dict(self, customer: Any) -> dict[str, Any]:
        data = self._safe_serialize(customer)
        data["street_address"] = self._flatten_street(data.get("street_address"))
        data["state_province"] = data.get("iso3166_2", "") or ""
        data["country"] = self._flatten_country(data.get("iso3166_1"))
        data["raw_data"] = data.copy()
        return data

    @staticmethod
    def _safe_serialize(obj: Any) -> dict:
        import json

        try:
            if hasattr(obj, "model_dump"):
                data = obj.model_dump()
            else:
                return {}
            # Round-trip through JSON to coerce non-serializable types (e.g. IPv4Address) to strings
            return json.loads(json.dumps(data, default=str))
        except Exception:
            return {}
