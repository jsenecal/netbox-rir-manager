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

    @staticmethod
    def _country_code(iso3166_1: Any) -> str:
        """Extract two-letter country code from an Iso31661 object."""
        if iso3166_1 is None:
            return ""
        return getattr(iso3166_1, "code2", "") or ""

    def _poc_to_dict(self, poc: Any) -> dict[str, Any]:
        email = ""
        if hasattr(poc, "emails") and poc.emails:
            email = poc.emails[0] if isinstance(poc.emails[0], str) else getattr(poc.emails[0], "email", "")
        phone = ""
        if hasattr(poc, "phones") and poc.phones:
            phone_obj = poc.phones[0]
            if isinstance(phone_obj, str):
                phone = phone_obj
            else:
                number = getattr(phone_obj, "number", "") or ""
                extension = getattr(phone_obj, "extension", "") or ""
                phone = f"{number}x{extension}" if extension else number
        return {
            "handle": poc.handle,
            "contact_type": poc.contact_type,
            "first_name": getattr(poc, "first_name", "") or "",
            "last_name": poc.last_name or "",
            "company_name": getattr(poc, "company_name", "") or "",
            "email": email,
            "phone": phone,
            "city": getattr(poc, "city", "") or "",
            "postal_code": getattr(poc, "postal_code", "") or "",
            "country": self._country_code(getattr(poc, "iso3166_1", None)),
            "raw_data": self._safe_serialize(poc),
        }

    def _org_to_dict(self, org: Any) -> dict[str, Any]:
        street = ""
        if hasattr(org, "street_address") and org.street_address:
            street = "\n".join(line.line for line in org.street_address if hasattr(line, "line") and line.line)
        poc_links = []
        if hasattr(org, "poc_links") and org.poc_links:
            for link in org.poc_links:
                poc_links.append(
                    {
                        "handle": link.handle,
                        "function": getattr(link, "function", ""),
                    }
                )
        return {
            "handle": org.handle,
            "name": org.org_name or "",
            "street_address": street,
            "city": getattr(org, "city", "") or "",
            "state_province": getattr(org, "iso3166_2", "") or "",
            "postal_code": getattr(org, "postal_code", "") or "",
            "country": self._country_code(getattr(org, "iso3166_1", None)),
            "poc_links": poc_links,
            "raw_data": self._safe_serialize(org),
        }

    def _net_to_dict(self, net: Any) -> dict[str, Any]:
        net_blocks: list[dict[str, Any]] = []
        if hasattr(net, "net_blocks") and net.net_blocks:
            for block in net.net_blocks:
                net_blocks.append(
                    {
                        "start_address": str(getattr(block, "start_address", "")),
                        "end_address": str(getattr(block, "end_address", "")),
                        "cidr_length": getattr(block, "cidr_length", None),
                        "type": getattr(block, "type", ""),
                    }
                )
        return {
            "handle": net.handle,
            "net_name": net.net_name or "",
            "version": getattr(net, "version", None),
            "org_handle": getattr(net, "org_handle", "") or "",
            "parent_net_handle": getattr(net, "parent_net_handle", "") or "",
            "net_blocks": net_blocks,
            "raw_data": self._safe_serialize(net),
        }

    def _ticket_request_to_dict(self, ticket_request: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        ticket = getattr(ticket_request, "ticket", None)
        if ticket:
            result["ticket_number"] = getattr(ticket, "ticket_no", "")
            result["ticket_status"] = getattr(ticket, "web_ticket_status", "")
            result["ticket_type"] = getattr(ticket, "web_ticket_type", "")
            result["ticket_resolution"] = getattr(ticket, "web_ticket_resolution", "")
            result["created_date"] = getattr(ticket, "created_date", "")
            result["resolved_date"] = getattr(ticket, "resolved_date", "")
            result["raw_data"] = self._safe_serialize(ticket)
        net = getattr(ticket_request, "net", None)
        if net:
            result["net"] = self._net_to_dict(net)
        return result

    def _customer_to_dict(self, customer: Any) -> dict[str, Any]:
        return {
            "handle": getattr(customer, "handle", ""),
            "customer_name": getattr(customer, "customer_name", ""),
            "parent_org_handle": getattr(customer, "parent_org_handle", ""),
            "raw_data": self._safe_serialize(customer),
        }

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
