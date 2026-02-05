from netbox_rir_manager.backends.base import RIRBackend


def test_backend_cannot_be_instantiated():
    """RIRBackend is abstract and should not be instantiated directly."""
    import pytest

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

    backend = TestBackend()
    assert backend.name == "TEST"
    assert backend.authenticate(None) is True
