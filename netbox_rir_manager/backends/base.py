from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from netbox_rir_manager.models import RIRConfig


class RIRBackend(ABC):
    """Abstract base class for RIR API backends."""

    name: str

    @abstractmethod
    def authenticate(self, rir_config: RIRConfig) -> bool:
        """Validate credentials and establish connection."""
        ...

    @abstractmethod
    def get_organization(self, handle: str) -> dict[str, Any] | None:
        """Retrieve organization details by handle."""
        ...

    @abstractmethod
    def get_network(self, handle: str) -> dict[str, Any] | None:
        """Retrieve network/prefix details."""
        ...

    @abstractmethod
    def get_poc(self, handle: str) -> dict[str, Any] | None:
        """Retrieve Point of Contact details."""
        ...

    @abstractmethod
    def get_asn(self, asn: int) -> dict[str, Any] | None:
        """Retrieve ASN details."""
        ...

    @abstractmethod
    def sync_resources(self, rir_config: RIRConfig, resource_type: str | None = None) -> list[dict[str, Any]]:
        """Sync resources from RIR. Returns list of synced resource dicts."""
        ...

    @abstractmethod
    def update_network(self, handle: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update a network's details (name, POC links, comments). Returns updated net dict or None."""
        ...

    @abstractmethod
    def reassign_network(self, parent_handle: str, net_data: dict[str, Any]) -> dict[str, Any] | None:
        """Reassign a subnet from parent NET. Returns ticket info dict or None."""
        ...

    @abstractmethod
    def reallocate_network(self, parent_handle: str, net_data: dict[str, Any]) -> dict[str, Any] | None:
        """Reallocate a subnet from parent NET. Returns ticket info dict or None."""
        ...

    @abstractmethod
    def remove_network(self, handle: str) -> bool:
        """Remove a reassigned/reallocated network. Returns True on success."""
        ...

    @abstractmethod
    def delete_network(self, handle: str) -> dict[str, Any] | None:
        """Delete a network. Returns ticket info dict or None."""
        ...

    @abstractmethod
    def get_customer(self, handle: str) -> dict[str, Any] | None:
        """Retrieve customer details by handle."""
        ...

    @abstractmethod
    def create_customer(self, parent_net_handle: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """Create a customer under a parent NET for simple reassignment. Returns customer dict or None."""
        ...
