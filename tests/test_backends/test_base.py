import pytest

from netbox_rir_manager.backends.base import RIRBackend


def test_backend_cannot_be_instantiated():
    """RIRBackend is abstract and should not be instantiated directly."""
    with pytest.raises(TypeError):
        RIRBackend()


def test_backend_subclass_works():
    """Concrete subclass can be instantiated."""

    class TestBackend(RIRBackend):
        name = "TEST"

        def authenticate(self, rir_config):
            return True

        def get_organization(self, handle):
            return {}

        def get_network(self, handle):
            return {}

        def get_poc(self, handle):
            return {}

        def get_asn(self, asn):
            return {}

        def sync_resources(self, rir_config, resource_type=None):
            return []

        def update_network(self, handle, data):
            return {}

        def reassign_network(self, parent_handle, net_data):
            return {}

        def reallocate_network(self, parent_handle, net_data):
            return {}

        def remove_network(self, handle):
            return True

        def delete_network(self, handle):
            return {}

        def create_customer(self, parent_net_handle, data):
            return {}

        def get_customer(self, handle):
            return {}

    backend = TestBackend()
    assert backend.name == "TEST"
    assert backend.authenticate(None) is True


def test_backend_missing_write_methods_cannot_be_instantiated():
    """A subclass missing write methods should not be instantiable."""

    class IncompleteBackend(RIRBackend):
        name = "INCOMPLETE"

        def authenticate(self, rir_config):
            return True

        def get_organization(self, handle):
            return {}

        def get_network(self, handle):
            return {}

        def get_poc(self, handle):
            return {}

        def get_asn(self, asn):
            return {}

        def sync_resources(self, rir_config, resource_type=None):
            return []

        # Deliberately missing: update_network, reassign_network,
        # reallocate_network, remove_network, delete_network, create_customer

    with pytest.raises(TypeError):
        IncompleteBackend()
