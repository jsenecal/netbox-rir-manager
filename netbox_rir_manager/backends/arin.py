from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from regrws.api.core import Api
from regrws.models import Error
from tenacity import RetryError, Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from netbox_rir_manager.backends import register_backend
from netbox_rir_manager.backends.base import RIRBackend

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from netbox_rir_manager.models import RIRConfig


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
        net = self._call_with_retry(self.api.net.from_handle, handle)
        if net is None or isinstance(net, Error):
            return None
        if "net_name" in data:
            net.net_name = data["net_name"]
        result = self._call_with_retry(net.save)
        if result is None or isinstance(result, Error):
            return None
        return self._net_to_dict(result)

    def reassign_network(self, parent_handle: str, net_data: dict[str, Any]) -> dict[str, Any] | None:
        parent = self._call_with_retry(self.api.net.from_handle, parent_handle)
        if parent is None or isinstance(parent, Error):
            return None
        from regrws.models import Net

        child_net = Net(**net_data)
        result = self._call_with_retry(self.api.net.reassign, parent, child_net)
        if result is None or isinstance(result, Error):
            return None
        return self._ticket_request_to_dict(result)

    def reallocate_network(self, parent_handle: str, net_data: dict[str, Any]) -> dict[str, Any] | None:
        parent = self._call_with_retry(self.api.net.from_handle, parent_handle)
        if parent is None or isinstance(parent, Error):
            return None
        from regrws.models import Net

        child_net = Net(**net_data)
        result = self._call_with_retry(self.api.net.reallocate, parent, child_net)
        if result is None or isinstance(result, Error):
            return None
        return self._ticket_request_to_dict(result)

    def remove_network(self, handle: str) -> bool:
        net = self._call_with_retry(self.api.net.from_handle, handle)
        if net is None or isinstance(net, Error):
            return False
        result = self._call_with_retry(self.api.net.remove, net)
        return not (result is None or isinstance(result, Error))

    def delete_network(self, handle: str) -> dict[str, Any] | None:
        net = self._call_with_retry(self.api.net.from_handle, handle)
        if net is None or isinstance(net, Error):
            return None
        result = self._call_with_retry(net.delete)
        if result is None or isinstance(result, Error):
            return None
        return self._ticket_request_to_dict(result)

    def get_customer(self, handle: str) -> dict[str, Any] | None:
        result = self._call_with_retry(self.api.customer.from_handle, handle)
        if result is None or isinstance(result, Error):
            return None
        return self._customer_to_dict(result)

    def create_customer(self, parent_net_handle: str, data: dict[str, Any]) -> dict[str, Any] | None:
        parent = self._call_with_retry(self.api.net.from_handle, parent_net_handle)
        if parent is None or isinstance(parent, Error):
            return None
        result = self._call_with_retry(self.api.customer.create_for_net, parent, **data)
        if result is None or isinstance(result, Error):
            return None
        return self._customer_to_dict(result)

    # ------------------------------------------------------------------
    # Internal helpers to normalise pyregrws models to plain dicts
    # ------------------------------------------------------------------

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
            if hasattr(obj, "dict"):
                data = obj.dict()
            else:
                return {}
            # Round-trip through JSON to coerce non-serializable types (e.g. IPv4Address) to strings
            return json.loads(json.dumps(data, default=str))
        except Exception:
            return {}
