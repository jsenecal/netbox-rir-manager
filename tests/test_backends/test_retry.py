from unittest.mock import MagicMock

import pytest
from regrws.models import Error


@pytest.mark.django_db
class TestARINBackendRetry:
    def test_get_organization_retries_on_exception(self):
        from netbox_rir_manager.backends.arin import ARINBackend

        backend = ARINBackend(api_key="test")
        mock_org = MagicMock()
        mock_org.handle = "TEST-ARIN"
        mock_org.org_name = "Test"
        mock_org.street_address = None
        mock_org.poc_links = None
        mock_org.city = ""
        mock_org.iso3166_2 = ""
        mock_org.postal_code = ""
        mock_org.iso3166_1 = None
        mock_org.dict.return_value = {
            "handle": "TEST-ARIN",
            "org_name": "Test",
            "street_address": None,
            "city": "",
            "iso3166_2": "",
            "postal_code": "",
            "iso3166_1": None,
        }

        # First two calls raise, third succeeds
        backend.api.org.from_handle = MagicMock(
            side_effect=[ConnectionError("timeout"), ConnectionError("timeout"), mock_org]
        )
        result = backend.get_organization("TEST-ARIN")
        assert result is not None
        assert result["handle"] == "TEST-ARIN"
        assert backend.api.org.from_handle.call_count == 3

    def test_get_organization_gives_up_after_max_retries(self):
        from netbox_rir_manager.backends.arin import ARINBackend

        backend = ARINBackend(api_key="test")
        backend.api.org.from_handle = MagicMock(side_effect=ConnectionError("timeout"))
        result = backend.get_organization("TEST-ARIN")
        assert result is None

    def test_get_poc_retries_on_exception(self):
        from netbox_rir_manager.backends.arin import ARINBackend

        backend = ARINBackend(api_key="test")
        mock_poc = MagicMock()
        mock_poc.handle = "JD1-ARIN"
        mock_poc.contact_type = "PERSON"
        mock_poc.first_name = "John"
        mock_poc.last_name = "Doe"
        mock_poc.company_name = ""
        mock_poc.emails = []
        mock_poc.phones = []
        mock_poc.city = ""
        mock_poc.postal_code = ""
        mock_poc.iso3166_1 = None
        mock_poc.dict.return_value = {
            "handle": "JD1-ARIN",
            "contact_type": "PERSON",
            "first_name": "John",
            "last_name": "Doe",
            "company_name": "",
            "emails": [],
            "phones": [],
            "city": "",
            "postal_code": "",
            "iso3166_1": None,
            "street_address": None,
            "iso3166_2": "",
        }

        backend.api.poc.from_handle = MagicMock(side_effect=[ConnectionError("fail"), mock_poc])
        result = backend.get_poc("JD1-ARIN")
        assert result is not None
        assert backend.api.poc.from_handle.call_count == 2

    def test_find_net_retries_on_exception(self):
        from netbox_rir_manager.backends.arin import ARINBackend

        backend = ARINBackend(api_key="test")
        mock_net = MagicMock()
        mock_net.handle = "NET-1"
        mock_net.net_name = "TEST"
        mock_net.version = 4
        mock_net.org_handle = ""
        mock_net.parent_net_handle = ""
        mock_net.net_blocks = []
        mock_net.dict.return_value = {
            "handle": "NET-1",
            "net_name": "TEST",
            "version": 4,
            "org_handle": "",
            "parent_net_handle": "",
            "net_blocks": [],
        }

        backend.api.net.find_net = MagicMock(side_effect=[ConnectionError("fail"), mock_net])
        result = backend.find_net("192.0.2.0", "192.0.2.255")
        assert result is not None
        assert backend.api.net.find_net.call_count == 2

    def test_no_retry_on_error_response(self):
        """Error objects from ARIN API should not trigger retries."""
        from netbox_rir_manager.backends.arin import ARINBackend

        backend = ARINBackend(api_key="test")
        backend.api.org.from_handle = MagicMock(return_value=Error(message="Not Found", code="E_OBJECT_NOT_FOUND"))
        result = backend.get_organization("NOEXIST")
        assert result is None
        assert backend.api.org.from_handle.call_count == 1
