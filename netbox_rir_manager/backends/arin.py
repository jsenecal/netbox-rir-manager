from __future__ import annotations

from typing import TYPE_CHECKING, Any

from regrws.api.core import Api
from regrws.models import Error

from netbox_rir_manager.backends import register_backend
from netbox_rir_manager.backends.base import RIRBackend

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

    def authenticate(self, rir_config: RIRConfig) -> bool:
        if not rir_config.org_handle:
            return False
        result = self.api.org.from_handle(rir_config.org_handle)
        return not isinstance(result, Error)

    def get_organization(self, handle: str) -> dict[str, Any] | None:
        result = self.api.org.from_handle(handle)
        if isinstance(result, Error):
            return None
        return self._org_to_dict(result)

    def get_network(self, handle: str) -> dict[str, Any] | None:
        result = self.api.net.from_handle(handle)
        if isinstance(result, Error):
            return None
        return self._net_to_dict(result)

    def get_poc(self, handle: str) -> dict[str, Any] | None:
        result = self.api.poc.from_handle(handle)
        if isinstance(result, Error):
            return None
        return self._poc_to_dict(result)

    def find_net(self, start_address: str, end_address: str) -> dict[str, Any] | None:
        """Find a network by start/end address range."""
        result = self.api.net.find_net(start_address, end_address)
        if isinstance(result, Error):
            return None
        return self._net_to_dict(result)

    def get_asn(self, asn: int) -> dict[str, Any] | None:
        return None

    def sync_resources(self, rir_config: RIRConfig, resource_type: str | None = None) -> list[dict[str, Any]]:
        return []

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
                poc_links.append({
                    "handle": link.handle,
                    "function": getattr(link, "function", ""),
                })
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

    @staticmethod
    def _safe_serialize(obj: Any) -> dict:
        try:
            if hasattr(obj, "dict"):
                return obj.dict()
            return {}
        except Exception:
            return {}
