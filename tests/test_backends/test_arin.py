import warnings
from unittest.mock import MagicMock, patch

import pytest
from regrws.models import Org
from regrws.models.nested import Iso31661, MultiLineElement

from netbox_rir_manager.backends.arin import ARINBackend
from netbox_rir_manager.backends.base import RIRBackend, RIRRequestError
from tests.arin_payloads import BAD_COUNTRY, NOT_FOUND, OVERLAP, arin_error

# The plugin's flat net data for a child net; CHILD_NET adds the recipient handle ARIN requires.
NET = {"net_name": "CUST-192-0-2-0-28", "start_address": "192.0.2.0", "end_address": "192.0.2.15"}
CHILD_NET = {**NET, "org_handle": "ORG-CHILD"}


def test_arin_backend_is_rir_backend():
    assert issubclass(ARINBackend, RIRBackend)


def test_safe_serialize_uses_pydantic_v2_model_dump():
    """_safe_serialize must serialize real pyregrws (pydantic v2) models cleanly.

    Regression: the v1-era ``.dict()`` call emits ``PydanticDeprecatedSince20``
    under pydantic v2. Combined with the broad ``except Exception`` in
    _safe_serialize, any warnings-as-errors context silently collapses every
    payload to ``{}`` -- i.e. orgs/pocs/nets serialize to empty dicts with no
    error. Serializing via ``model_dump()`` avoids the deprecated path.
    """
    org = Org(
        org_name="EXAMPLE-ORG",
        street_address=[MultiLineElement(number=1, line="123 Main St")],
        city="Anytown",
        iso3166_1=Iso31661(code2="US"),
        iso3166_2="CA",
        postal_code="90210",
        handle="ORG-1",
        poc_links=[],
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        data = ARINBackend._safe_serialize(org)

    assert data.get("org_name") == "EXAMPLE-ORG"
    assert data.get("handle") == "ORG-1"


def test_arin_backend_name():
    assert ARINBackend.name == "ARIN"


@patch("netbox_rir_manager.backends.arin.Api")
def test_arin_backend_init(mock_api_class):
    backend = ARINBackend(api_key="test-key")
    assert backend.api is not None
    mock_api_class.assert_called_once_with(api_key="test-key")


@patch("netbox_rir_manager.backends.arin.Api")
def test_arin_backend_init_custom_url(mock_api_class):
    backend = ARINBackend(api_key="test-key", base_url="https://reg.ote.arin.net/")
    assert backend.api is not None
    mock_api_class.assert_called_once_with(api_key="test-key", base_url="https://reg.ote.arin.net/")


@patch("netbox_rir_manager.backends.arin.Api")
def test_for_user_key(mock_api_class):
    """for_user_key acts with the key's own api_key against its config's API URL."""
    user_key = MagicMock(api_key="user-key")
    user_key.rir_config.api_url = "https://reg.ote.arin.net/"

    backend = ARINBackend.for_user_key(user_key)
    assert isinstance(backend, ARINBackend)
    mock_api_class.assert_called_once_with(api_key="user-key", base_url="https://reg.ote.arin.net/")


@patch("netbox_rir_manager.backends.arin.Api")
def test_for_user_key_no_api_url(mock_api_class):
    """A config without an API URL leaves pyregrws on its default endpoint."""
    user_key = MagicMock(api_key="user-key")
    user_key.rir_config.api_url = ""

    ARINBackend.for_user_key(user_key)
    mock_api_class.assert_called_once_with(api_key="user-key")


@patch("netbox_rir_manager.backends.arin.Api")
def test_authenticate_success(mock_api_class):
    mock_api = MagicMock()
    mock_org = MagicMock()  # Not an Error instance
    mock_api.org.from_handle.return_value = mock_org
    mock_api_class.return_value = mock_api

    rir_config = MagicMock()
    rir_config.org_handle = "EXAMPLE-ARIN"

    backend = ARINBackend(api_key="test-key")
    assert backend.authenticate(rir_config) is True
    mock_api.org.from_handle.assert_called_once_with("EXAMPLE-ARIN")


@patch("netbox_rir_manager.backends.arin.Api")
def test_authenticate_no_org_handle(mock_api_class):
    rir_config = MagicMock()
    rir_config.org_handle = ""

    backend = ARINBackend(api_key="test-key")
    assert backend.authenticate(rir_config) is False


@patch("netbox_rir_manager.backends.arin.Api")
def test_authenticate_error(mock_api_class):
    """When the API returns an Error, authenticate should return False."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    # Patch Error so isinstance check works with our mock
    from netbox_rir_manager.backends import arin as arin_mod

    real_error_class = arin_mod.Error
    mock_error = MagicMock(spec=real_error_class)
    mock_error.__class__ = real_error_class
    mock_api.org.from_handle.return_value = mock_error

    rir_config = MagicMock()
    rir_config.org_handle = "BADHANDLE"

    backend = ARINBackend(api_key="test-key")
    with patch.object(arin_mod, "Error", real_error_class):
        assert backend.authenticate(rir_config) is False


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_poc(mock_api_class):
    mock_api = MagicMock()
    mock_poc = MagicMock()
    mock_poc.handle = "JD123-ARIN"
    mock_poc.last_name = "Doe"
    mock_poc.first_name = "John"
    mock_poc.contact_type = "PERSON"
    mock_poc.company_name = "Example Corp"
    mock_poc.city = "Anytown"
    mock_poc.postal_code = "12345"
    mock_poc.iso3166_1 = MagicMock(code2="US")
    mock_poc.model_dump.return_value = {
        "handle": "JD123-ARIN",
        "last_name": "Doe",
        "first_name": "John",
        "contact_type": "PERSON",
        "company_name": "Example Corp",
        "city": "Anytown",
        "postal_code": "12345",
        "iso3166_1": {"code2": "US"},
        "emails": ["jdoe@example.com"],
        "phones": [],
        "street_address": None,
        "iso3166_2": "",
    }
    mock_api.poc.from_handle.return_value = mock_poc
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_poc("JD123-ARIN")

    mock_api.poc.from_handle.assert_called_once_with("JD123-ARIN")
    assert result is not None
    assert result["handle"] == "JD123-ARIN"
    assert result["first_name"] == "John"
    assert result["last_name"] == "Doe"
    assert result["contact_type"] == "PERSON"
    assert result["company_name"] == "Example Corp"
    assert result["city"] == "Anytown"
    assert result["postal_code"] == "12345"
    assert result["country"] == "US"
    assert "raw_data" in result


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_poc_no_country(mock_api_class):
    """When iso3166_1 is None, country should be empty string."""
    mock_api = MagicMock()
    mock_poc = MagicMock()
    mock_poc.handle = "JD123-ARIN"
    mock_poc.last_name = "Doe"
    mock_poc.contact_type = "PERSON"
    mock_poc.iso3166_1 = None
    mock_poc.model_dump.return_value = {
        "handle": "JD123-ARIN",
        "last_name": "Doe",
        "contact_type": "PERSON",
        "iso3166_1": None,
        "emails": [],
        "phones": [],
        "street_address": None,
        "iso3166_2": "",
    }
    mock_api.poc.from_handle.return_value = mock_poc
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_poc("JD123-ARIN")

    assert result is not None
    assert result["country"] == ""


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_organization(mock_api_class):
    mock_api = MagicMock()
    mock_org = MagicMock()
    mock_org.handle = "EXAMPLE-ARIN"
    mock_org.org_name = "Example Corp"
    mock_org.street_address = None
    mock_org.city = "Anytown"
    mock_org.iso3166_2 = "VA"
    mock_org.postal_code = "12345"
    mock_org.iso3166_1 = MagicMock(code2="US")
    mock_org.model_dump.return_value = {
        "handle": "EXAMPLE-ARIN",
        "org_name": "Example Corp",
        "street_address": None,
        "city": "Anytown",
        "iso3166_2": "VA",
        "postal_code": "12345",
        "iso3166_1": {"code2": "US"},
    }
    mock_api.org.from_handle.return_value = mock_org
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_organization("EXAMPLE-ARIN")

    mock_api.org.from_handle.assert_called_once_with("EXAMPLE-ARIN")
    assert result is not None
    assert result["handle"] == "EXAMPLE-ARIN"
    assert result["name"] == "Example Corp"
    assert result["street_address"] == ""
    assert result["city"] == "Anytown"
    assert result["state_province"] == "VA"
    assert result["postal_code"] == "12345"
    assert result["country"] == "US"
    assert "raw_data" in result


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_organization_with_street_address(mock_api_class):
    mock_api = MagicMock()
    mock_org = MagicMock()
    mock_org.handle = "EXAMPLE-ARIN"
    mock_org.org_name = "Example Corp"
    line1 = MagicMock()
    line1.line = "123 Main St"
    line2 = MagicMock()
    line2.line = "Suite 100"
    mock_org.street_address = [line1, line2]
    mock_org.city = "Anytown"
    mock_org.iso3166_2 = "VA"
    mock_org.postal_code = "12345"
    mock_org.iso3166_1 = MagicMock(code2="US")
    mock_org.model_dump.return_value = {
        "handle": "EXAMPLE-ARIN",
        "org_name": "Example Corp",
        "street_address": [{"line": "123 Main St"}, {"line": "Suite 100"}],
        "city": "Anytown",
        "iso3166_2": "VA",
        "postal_code": "12345",
        "iso3166_1": {"code2": "US"},
    }
    mock_api.org.from_handle.return_value = mock_org
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_organization("EXAMPLE-ARIN")

    assert result is not None
    assert result["street_address"] == "123 Main St\nSuite 100"


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_network(mock_api_class):
    mock_api = MagicMock()
    mock_net = MagicMock()
    mock_net.handle = "NET-192-0-2-0-1"
    mock_net.net_name = "EXAMPLE-NET"
    mock_net.version = 4
    mock_net.org_handle = "EXAMPLE-ARIN"
    mock_net.parent_net_handle = ""
    mock_net.net_blocks = None
    mock_net.model_dump.return_value = {
        "handle": "NET-192-0-2-0-1",
        "net_name": "EXAMPLE-NET",
        "version": 4,
        "org_handle": "EXAMPLE-ARIN",
        "parent_net_handle": "",
        "net_blocks": None,
    }
    mock_api.net.from_handle.return_value = mock_net
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_network("NET-192-0-2-0-1")

    mock_api.net.from_handle.assert_called_once_with("NET-192-0-2-0-1")
    assert result is not None
    assert result["handle"] == "NET-192-0-2-0-1"
    assert result["net_name"] == "EXAMPLE-NET"
    assert result["version"] == 4
    assert result["org_handle"] == "EXAMPLE-ARIN"
    assert result["net_blocks"] is None
    assert "raw_data" in result


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_network_with_blocks(mock_api_class):
    mock_api = MagicMock()
    mock_net = MagicMock()
    mock_net.handle = "NET-192-0-2-0-1"
    mock_net.net_name = "EXAMPLE-NET"
    mock_net.version = 4
    mock_net.org_handle = "EXAMPLE-ARIN"
    mock_net.parent_net_handle = ""

    block = MagicMock()
    block.start_address = "192.0.2.0"
    block.end_address = "192.0.2.255"
    block.cidr_length = 24
    block.type = "A"
    mock_net.net_blocks = [block]
    mock_net.model_dump.return_value = {
        "handle": "NET-192-0-2-0-1",
        "net_name": "EXAMPLE-NET",
        "version": 4,
        "org_handle": "EXAMPLE-ARIN",
        "parent_net_handle": "",
        "net_blocks": [{"start_address": "192.0.2.0", "end_address": "192.0.2.255", "cidr_length": 24, "type": "A"}],
    }

    mock_api.net.from_handle.return_value = mock_net
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_network("NET-192-0-2-0-1")

    assert result is not None
    assert len(result["net_blocks"]) == 1
    assert result["net_blocks"][0]["start_address"] == "192.0.2.0"
    assert result["net_blocks"][0]["end_address"] == "192.0.2.255"
    assert result["net_blocks"][0]["cidr_length"] == 24
    assert result["net_blocks"][0]["type"] == "A"


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_poc_error_returns_none(mock_api_class):
    """When pyregrws returns an Error object, get_poc should return None."""
    from netbox_rir_manager.backends import arin as arin_mod

    mock_api = MagicMock()
    error_cls = arin_mod.Error
    mock_error = MagicMock(spec=error_cls)
    mock_error.__class__ = error_cls
    mock_api.poc.from_handle.return_value = mock_error
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_poc("NONEXISTENT-ARIN")
    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_organization_error_returns_none(mock_api_class):
    """When pyregrws returns an Error object, get_organization should return None."""
    from netbox_rir_manager.backends import arin as arin_mod

    mock_api = MagicMock()
    error_cls = arin_mod.Error
    mock_error = MagicMock(spec=error_cls)
    mock_error.__class__ = error_cls
    mock_api.org.from_handle.return_value = mock_error
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_organization("NONEXISTENT-ARIN")
    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_network_error_returns_none(mock_api_class):
    """When pyregrws returns an Error object, get_network should return None."""
    from netbox_rir_manager.backends import arin as arin_mod

    mock_api = MagicMock()
    error_cls = arin_mod.Error
    mock_error = MagicMock(spec=error_cls)
    mock_error.__class__ = error_cls
    mock_api.net.from_handle.return_value = mock_error
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    result = backend.get_network("NONEXISTENT-NET")
    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_asn_returns_none(mock_api_class):
    """get_asn is not yet implemented and should return None."""
    backend = ARINBackend(api_key="test-key")
    assert backend.get_asn(12345) is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_sync_resources_returns_empty(mock_api_class):
    """sync_resources is not yet implemented and should return empty list."""
    rir_config = MagicMock()
    backend = ARINBackend(api_key="test-key")
    assert backend.sync_resources(rir_config) == []


@patch("netbox_rir_manager.backends.arin.Api")
def test_backend_registered(mock_api_class):
    """ARINBackend should be auto-registered in BACKENDS dict."""
    from netbox_rir_manager.backends import BACKENDS, get_backend

    assert "ARIN" in BACKENDS
    assert get_backend("ARIN") is ARINBackend


def _make_mock_net(**overrides):
    """Create a MagicMock that looks like a pyregrws Net."""
    defaults = {
        "handle": "NET-TEST",
        "net_name": "TEST-NET",
        "version": 4,
        "org_handle": "TEST-ORG",
        "parent_net_handle": "",
        "net_blocks": [],
    }
    defaults.update(overrides)
    mock_net = MagicMock()
    for key, value in defaults.items():
        setattr(mock_net, key, value)
    mock_net.model_dump.return_value = dict(defaults)
    return mock_net


def _make_mock_ticket_request(ticket_no="TKT-001", net=None):
    """Create a MagicMock that looks like a pyregrws TicketRequest."""
    ticket_data = {
        "ticket_no": ticket_no,
        "web_ticket_status": "PENDING_REVIEW",
        "web_ticket_type": "IPV4_SIMPLE_REASSIGN",
        "web_ticket_resolution": "",
        "created_date": "2026-02-05",
        "resolved_date": "",
    }
    mock_ticket = MagicMock()
    for key, value in ticket_data.items():
        setattr(mock_ticket, key, value)
    mock_ticket.model_dump.return_value = dict(ticket_data)

    mock_ticket_request = MagicMock()
    mock_ticket_request.ticket = mock_ticket
    mock_ticket_request.net = net
    return mock_ticket_request


# ------------------------------------------------------------------
# update_network tests
# ------------------------------------------------------------------


@patch("netbox_rir_manager.backends.arin.Api")
def test_update_network_success(mock_api_class):
    """update_network should fetch, update, save, and return the net dict."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_net = _make_mock_net(handle="NET-TEST", net_name="OLD-NAME")
    saved_net = _make_mock_net(handle="NET-TEST", net_name="NEW-NAME")
    mock_net.save.return_value = saved_net

    mock_api.net.from_handle.return_value = mock_net

    backend = ARINBackend(api_key="test-key")
    result = backend.update_network("NET-TEST", {"net_name": "NEW-NAME"})

    assert result is not None
    assert result["handle"] == "NET-TEST"
    assert result["net_name"] == "NEW-NAME"
    assert mock_net.net_name == "NEW-NAME"
    mock_net.save.assert_called_once()


@patch("netbox_rir_manager.backends.arin.Api")
def test_update_network_no_changes(mock_api_class):
    """update_network with empty data should still save and return."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_net = _make_mock_net(handle="NET-TEST", net_name="ORIGINAL")
    mock_net.save.return_value = mock_net

    mock_api.net.from_handle.return_value = mock_net

    backend = ARINBackend(api_key="test-key")
    result = backend.update_network("NET-TEST", {})

    assert result is not None
    assert result["handle"] == "NET-TEST"
    mock_net.save.assert_called_once()


@patch("netbox_rir_manager.backends.arin.Api")
def test_update_network_error_on_fetch(mock_api_class):
    """update_network raises RIRRequestError with ARIN's reason when the lookup returns an Error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = arin_error("not_found")

    backend = ARINBackend(api_key="test-key")
    with pytest.raises(RIRRequestError) as excinfo:
        backend.update_network("NET-BAD", {"net_name": "X"})

    assert str(excinfo.value) == NOT_FOUND


@patch("netbox_rir_manager.backends.arin.Api")
def test_update_network_error_on_save(mock_api_class):
    """update_network raises RIRRequestError with ARIN's reason when the save returns an Error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_net = _make_mock_net()
    mock_net.save.return_value = arin_error("overlap")
    mock_api.net.from_handle.return_value = mock_net

    backend = ARINBackend(api_key="test-key")
    with pytest.raises(RIRRequestError) as excinfo:
        backend.update_network("NET-TEST", {"net_name": "X"})

    assert str(excinfo.value) == OVERLAP


@patch("netbox_rir_manager.backends.arin.Api")
def test_update_network_none_on_fetch(mock_api_class):
    """update_network should return None when the fetch returns None (connection failure)."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.update_network("NET-BAD", {})

    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_update_network_none_on_save(mock_api_class):
    """update_network should return None when the save returns None (connection failure)."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_net = _make_mock_net()
    mock_net.save.return_value = None
    mock_api.net.from_handle.return_value = mock_net

    backend = ARINBackend(api_key="test-key")

    assert backend.update_network("NET-TEST", {"net_name": "X"}) is None


# ------------------------------------------------------------------
# reassign_network tests
# ------------------------------------------------------------------


@patch("netbox_rir_manager.backends.arin.Api")
def test_reassign_network_success(mock_api_class):
    """reassign_network should return ticket info on success."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_parent = _make_mock_net(handle="NET-PARENT")
    mock_ticket_request = _make_mock_ticket_request(ticket_no="TKT-001")

    mock_api.net.from_handle.return_value = mock_parent
    mock_api.net.reassign.return_value = mock_ticket_request

    backend = ARINBackend(api_key="test-key")
    result = backend.reassign_network("NET-PARENT", CHILD_NET)

    assert result is not None
    assert result["ticket_number"] == "TKT-001"
    assert result["ticket_status"] == "PENDING_REVIEW"
    assert result["ticket_type"] == "IPV4_SIMPLE_REASSIGN"
    assert result["created_date"] == "2026-02-05"


@patch("netbox_rir_manager.backends.arin.Api")
def test_reassign_network_with_net_in_response(mock_api_class):
    """reassign_network should include net dict when ticket_request has a net."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_parent = _make_mock_net(handle="NET-PARENT")
    child_net = _make_mock_net(handle="NET-CHILD", net_name="CHILD-NET")
    mock_ticket_request = _make_mock_ticket_request(ticket_no="TKT-002", net=child_net)

    mock_api.net.from_handle.return_value = mock_parent
    mock_api.net.reassign.return_value = mock_ticket_request

    backend = ARINBackend(api_key="test-key")
    result = backend.reassign_network("NET-PARENT", CHILD_NET)

    assert result is not None
    assert "net" in result
    assert result["net"]["handle"] == "NET-CHILD"


@patch("netbox_rir_manager.backends.arin.Api")
def test_reassign_network_none_on_parent_fetch(mock_api_class):
    """reassign_network should return None when parent fetch returns None."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.reassign_network("NET-BAD", CHILD_NET)

    assert result is None


# ------------------------------------------------------------------
# reallocate_network tests
# ------------------------------------------------------------------


@patch("netbox_rir_manager.backends.arin.Api")
def test_reallocate_network_success(mock_api_class):
    """reallocate_network should return ticket info on success."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_parent = _make_mock_net(handle="NET-PARENT")
    mock_ticket_request = _make_mock_ticket_request(ticket_no="TKT-010")

    mock_api.net.from_handle.return_value = mock_parent
    mock_api.net.reallocate.return_value = mock_ticket_request

    backend = ARINBackend(api_key="test-key")
    result = backend.reallocate_network("NET-PARENT", CHILD_NET)

    assert result is not None
    assert result["ticket_number"] == "TKT-010"
    assert result["ticket_status"] == "PENDING_REVIEW"


@patch("netbox_rir_manager.backends.arin.Api")
def test_reallocate_network_none_on_parent_fetch(mock_api_class):
    """reallocate_network should return None when parent fetch returns None."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.reallocate_network("NET-BAD", CHILD_NET)

    assert result is None


# ------------------------------------------------------------------
# remove_network tests
# ------------------------------------------------------------------


@patch("netbox_rir_manager.backends.arin.Api")
def test_remove_network_success(mock_api_class):
    """remove_network should return True on success."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_net = _make_mock_net(handle="NET-TEST")
    mock_result = MagicMock()  # TicketRequest, not Error
    mock_api.net.from_handle.return_value = mock_net
    mock_api.net.remove.return_value = mock_result

    backend = ARINBackend(api_key="test-key")
    result = backend.remove_network("NET-TEST")

    assert result is True
    mock_api.net.remove.assert_called_once_with(mock_net)


@patch("netbox_rir_manager.backends.arin.Api")
def test_remove_network_none_on_fetch(mock_api_class):
    """remove_network should return False when the fetch returns None."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.remove_network("NET-BAD")

    assert result is False


@patch("netbox_rir_manager.backends.arin.Api")
def test_remove_network_none_on_remove(mock_api_class):
    """remove_network should return False when remove returns None (connection failure)."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_net = _make_mock_net(handle="NET-TEST")
    mock_api.net.from_handle.return_value = mock_net
    mock_api.net.remove.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.remove_network("NET-TEST")

    assert result is False


# ------------------------------------------------------------------
# delete_network tests
# ------------------------------------------------------------------


@patch("netbox_rir_manager.backends.arin.Api")
def test_delete_network_success(mock_api_class):
    """delete_network should return ticket info on success."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_net = _make_mock_net(handle="NET-TEST")
    mock_ticket_request = _make_mock_ticket_request(ticket_no="TKT-DEL-001")
    mock_net.delete.return_value = mock_ticket_request
    mock_api.net.from_handle.return_value = mock_net

    backend = ARINBackend(api_key="test-key")
    result = backend.delete_network("NET-TEST")

    assert result is not None
    assert result["ticket_number"] == "TKT-DEL-001"
    assert result["ticket_status"] == "PENDING_REVIEW"
    mock_net.delete.assert_called_once()


@patch("netbox_rir_manager.backends.arin.Api")
def test_delete_network_none_on_fetch(mock_api_class):
    """delete_network should return None when the fetch returns None."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.delete_network("NET-BAD")

    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_delete_network_none_on_delete(mock_api_class):
    """delete_network should return None when delete returns None."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_net = _make_mock_net(handle="NET-TEST")
    mock_net.delete.return_value = None
    mock_api.net.from_handle.return_value = mock_net

    backend = ARINBackend(api_key="test-key")
    result = backend.delete_network("NET-TEST")

    assert result is None


# ------------------------------------------------------------------
# get_customer tests
# ------------------------------------------------------------------


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_customer_success(mock_api_class):
    """get_customer should return a flattened customer dict."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_customer = MagicMock()
    mock_customer.model_dump.return_value = {
        "handle": "C07654321",
        "customer_name": "Acme Corp",
        "street_address": [{"line": "123 Main St"}, {"line": "Suite 200"}],
        "city": "Anytown",
        "iso3166_2": "VA",
        "postal_code": "12345",
        "iso3166_1": {"code2": "US"},
        "registration_date": "2024-01-15",
    }
    mock_api.customer.from_handle.return_value = mock_customer

    backend = ARINBackend(api_key="test-key")
    result = backend.get_customer("C07654321")

    mock_api.customer.from_handle.assert_called_once_with("C07654321")
    assert result is not None
    assert result["handle"] == "C07654321"
    assert result["customer_name"] == "Acme Corp"
    assert result["street_address"] == "123 Main St\nSuite 200"
    assert result["state_province"] == "VA"
    assert result["country"] == "US"
    assert "raw_data" in result


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_customer_error_returns_none(mock_api_class):
    """get_customer should return None when the API returns an Error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.customer.from_handle.return_value = arin_error("not_found")

    backend = ARINBackend(api_key="test-key")
    result = backend.get_customer("C-NONEXISTENT")

    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_get_customer_none_returns_none(mock_api_class):
    """get_customer should return None when the API returns None."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.customer.from_handle.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.get_customer("C-NONEXISTENT")

    assert result is None


# ------------------------------------------------------------------
# create_customer tests
# ------------------------------------------------------------------

CUSTOMER = {
    "customer_name": "Test Customer",
    "street_address": "151 Front St W",
    "city": "Toronto",
    "state_province": "ON",
    "postal_code": "M5J 2N1",
    "country": "CA",
}


@patch("netbox_rir_manager.backends.arin.Api")
def test_create_customer_success(mock_api_class):
    """create_customer should return customer dict on success."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_parent = _make_mock_net(handle="NET-PARENT")
    mock_customer = MagicMock()
    mock_customer.handle = "C-TEST"
    mock_customer.customer_name = "Test Customer"
    mock_customer.parent_org_handle = "ORG-TEST"
    mock_customer.model_dump.return_value = {
        "handle": "C-TEST",
        "customer_name": "Test Customer",
        "parent_org_handle": "ORG-TEST",
    }

    mock_api.net.from_handle.return_value = mock_parent
    mock_api.customer.create_for_net.return_value = mock_customer

    backend = ARINBackend(api_key="test-key")
    result = backend.create_customer("NET-PARENT", CUSTOMER)

    assert result is not None
    assert result["handle"] == "C-TEST"
    assert result["customer_name"] == "Test Customer"
    assert result["parent_org_handle"] == "ORG-TEST"
    assert "raw_data" in result


@patch("netbox_rir_manager.backends.arin.Api")
def test_create_customer_none_on_parent_fetch(mock_api_class):
    """create_customer should return None when parent fetch returns None."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.create_customer("NET-BAD", CUSTOMER)

    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_create_customer_none_on_create(mock_api_class):
    """create_customer should return None when create_for_net returns None."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_parent = _make_mock_net(handle="NET-PARENT")
    mock_api.net.from_handle.return_value = mock_parent
    mock_api.customer.create_for_net.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.create_customer("NET-PARENT", CUSTOMER)

    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_create_customer_maps_flat_dict_to_pyregrws_customer(mock_api_class):
    """The flat customer dict is mapped to the fields pyregrws' Customer wants.

    Accented letters are transliterated (Reg-RWS payloads are ASCII-only), the street address
    becomes numbered lines and empty optional fields are left out.
    """
    from regrws.models import Customer

    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = _make_mock_net(handle="NET-PARENT")
    mock_api.customer.create_for_net.return_value = None

    backend = ARINBackend(api_key="test-key")
    backend.create_customer(
        "NET-PARENT",
        {
            "customer_name": "\u00c9nergie Qu\u00e9bec",
            "street_address": "1000 rue de la Gaucheti\u00e8re\n\nBureau 200 ",
            "city": "Montr\u00e9al",
            "state_province": "qc",
            "postal_code": "",
            "country": "ca",
        },
    )

    args, kwargs = mock_api.customer.create_for_net.call_args
    customer = Customer(**kwargs)
    assert args[0].handle == "NET-PARENT"
    assert customer.customer_name == "Energie Quebec"
    assert [(line.number, line.line) for line in customer.street_address] == [
        (1, "1000 rue de la Gauchetiere"),
        (2, "Bureau 200"),
    ]
    assert customer.city == "Montreal"
    assert customer.iso3166_1.code2 == "CA"
    assert customer.iso3166_2 == "QC"
    assert customer.postal_code is None


@pytest.mark.parametrize(
    "overrides, field",
    [
        pytest.param({"country": ""}, "iso3166_1", id="missing-country"),
        pytest.param({"state_province": "Quebec"}, "iso3166_2", id="subdivision-name-not-code"),
    ],
)
@patch("netbox_rir_manager.backends.arin.Api")
def test_create_customer_rejects_invalid_data_before_calling_arin(mock_api_class, overrides, field):
    """Data pyregrws refuses raises RIRDataError naming the field, not a ValidationError."""
    from netbox_rir_manager.backends.base import RIRDataError

    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    with pytest.raises(RIRDataError, match=field):
        backend.create_customer("NET-PARENT", {**CUSTOMER, **overrides})

    mock_api.net.from_handle.assert_not_called()


@pytest.mark.parametrize("handles", [{}, {"org_handle": "ORG-X"}], ids=["no-handle-yet", "org-handle"])
def test_validate_reassignment_accepts_a_valid_net(handles):
    """A simple reassignment's net has no customer handle until the customer exists at ARIN."""
    ARINBackend(api_key="test-key").validate_reassignment({**NET, **handles})


@patch("netbox_rir_manager.backends.arin.Api")
def test_net_payload_model_error_has_no_empty_location(mock_api_class):
    """A model-level refusal (no field location) reads cleanly."""
    from netbox_rir_manager.backends.base import RIRDataError

    with pytest.raises(RIRDataError) as excinfo:
        ARINBackend(api_key="test-key").reallocate_network("NET-PARENT", NET)

    assert str(excinfo.value).startswith("Invalid Net details for ARIN: Value error, either `org_handle`")


@patch("netbox_rir_manager.backends.arin.Api")
def test_net_payload_unparseable_start_address_names_only_that_field(mock_api_class):
    from netbox_rir_manager.backends.base import RIRDataError

    with pytest.raises(RIRDataError) as excinfo:
        ARINBackend(api_key="test-key").reallocate_network(
            "NET-PARENT", {**NET, "start_address": "192.0.2", "org_handle": "ORG-X"}
        )

    assert str(excinfo.value).startswith("Invalid Net details for ARIN: start_address: ")
    assert "version" not in str(excinfo.value)


@pytest.mark.parametrize("method", ["reassign_network", "reallocate_network"])
@patch("netbox_rir_manager.backends.arin.Api")
def test_net_payload_pyregrws_refuses_raises_rir_data_error(mock_api_class, method):
    """A Net payload pyregrws refuses raises RIRDataError naming the field instead of a ValidationError."""
    from netbox_rir_manager.backends.base import RIRDataError

    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    backend = ARINBackend(api_key="test-key")
    with pytest.raises(RIRDataError, match=r"Invalid Net details for ARIN: net_blocks\.0\.end_address: "):
        getattr(backend, method)("NET-PARENT", {**CHILD_NET, "end_address": "192.0.2.300"})

    mock_api.net.from_handle.assert_not_called()


@pytest.mark.parametrize(
    "method, verb, net_data, version, block_type, handle_field",
    [
        pytest.param(
            "reassign_network",
            "reassign",
            {
                "net_name": "CUST-192-0-2-0-28",
                "start_address": "192.0.2.0",
                "end_address": "192.0.2.15",
                "customer_handle": "C01234567",
            },
            4,
            "S",
            "customer_handle",
            id="reassign-ipv4",
        ),
        pytest.param(
            "reassign_network",
            "reassign",
            {
                "net_name": "CUST-2001-DB8-48",
                "start_address": "2001:db8::",
                "end_address": "2001:db8:0:ffff:ffff:ffff:ffff:ffff",
                "org_handle": "ORG-X",
            },
            6,
            "S",
            "org_handle",
            id="reassign-ipv6",
        ),
        pytest.param(
            "reallocate_network",
            "reallocate",
            {
                "net_name": "DOWN-198-51-100-0-24",
                "start_address": "198.51.100.0",
                "end_address": "198.51.100.255",
                "org_handle": "ORG-DOWN",
            },
            4,
            "A",
            "org_handle",
            id="reallocate-ipv4",
        ),
    ],
)
@patch("netbox_rir_manager.backends.arin.Api")
def test_net_payload_builds_real_pyregrws_net(
    mock_api_class, method, verb, net_data, version, block_type, handle_field
):
    """The plugin's flat net data becomes a Net pyregrws accepts.

    Net is not mocked here: version comes from the start address, and the range goes in one
    net block typed S (reassigned) or A (reallocated). parentNetHandle must name the parent
    in the request URL, or ARIN refuses the request (seen against ARIN OT&E).
    """
    from ipaddress import ip_address

    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = _make_mock_net(handle="NET-PARENT")
    getattr(mock_api.net, verb).return_value = None

    backend = ARINBackend(api_key="test-key")
    getattr(backend, method)("NET-PARENT", net_data)

    child = getattr(mock_api.net, verb).call_args[0][1]
    assert child.version == version
    assert child.net_name == net_data["net_name"]
    assert child.parent_net_handle == "NET-PARENT"
    assert getattr(child, handle_field) == net_data[handle_field]
    [block] = child.net_blocks
    assert block.type == block_type
    assert block.start_address == ip_address(net_data["start_address"])
    assert block.end_address == ip_address(net_data["end_address"])


# ------------------------------------------------------------------
# ARIN refusing a write
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, expected",
    [
        pytest.param("bad_country", BAD_COUNTRY, id="one-component"),
        pytest.param(
            "two_components",
            "postalCode: Postal code not in the correct format for country selected. "
            "iso3166-2: Value is required if the country selected is US or Canada.",
            id="two-components",
        ),
        pytest.param("authentication", "The API key specified was missing or invalid.", id="no-components"),
    ],
)
def test_error_detail_prefers_components_over_the_generic_message(name, expected):
    from netbox_rir_manager.backends.arin import error_detail

    assert error_detail(arin_error(name)) == expected


def test_error_detail_appends_additional_info():
    from regrws.models import Error

    from netbox_rir_manager.backends.arin import error_detail

    error = Error(message="Request failed.", code="E_UNSPECIFIED", additional_info=["Try again later."])
    assert error_detail(error) == "Request failed. Try again later."


def _refusing_api(mock_api_class, step, error):
    """An Api mock whose parent lookup, or the write itself (step "write"), returns error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    net = _make_mock_net(handle="NET-PARENT")
    mock_api.net.from_handle.return_value = error if step == "lookup" else net
    if step == "write":
        mock_api.net.reassign.return_value = error
        mock_api.net.reallocate.return_value = error
        mock_api.net.remove.return_value = error
        net.delete.return_value = error
        mock_api.customer.create_for_net.return_value = error
    return mock_api


WRITES = {
    "reassign": lambda backend: backend.reassign_network("NET-PARENT", CHILD_NET),
    "reallocate": lambda backend: backend.reallocate_network("NET-PARENT", CHILD_NET),
    "remove": lambda backend: backend.remove_network("NET-PARENT"),
    "delete": lambda backend: backend.delete_network("NET-PARENT"),
    "create_customer": lambda backend: backend.create_customer("NET-PARENT", CUSTOMER),
}


@pytest.mark.parametrize("write", WRITES)
@pytest.mark.parametrize(
    "step, name, detail", [("lookup", "not_found", NOT_FOUND), ("write", "overlap", OVERLAP)], ids=["lookup", "write"]
)
@patch("netbox_rir_manager.backends.arin.Api")
def test_write_refused_by_arin_raises_its_reason(mock_api_class, write, step, name, detail):
    """An Error from ARIN, on the parent lookup or the write itself, raises RIRRequestError with ARIN's reason."""
    _refusing_api(mock_api_class, step, arin_error(name))

    with pytest.raises(RIRRequestError) as excinfo:
        WRITES[write](ARINBackend(api_key="test-key"))

    assert str(excinfo.value) == detail


@pytest.mark.parametrize("country", ["XX", "XK", "uk"])
@patch("netbox_rir_manager.backends.arin.Api")
def test_create_customer_rejects_unknown_country_before_calling_arin(mock_api_class, country):
    """A two-letter code that is not ISO 3166-1 alpha-2 is a data error, not a round trip to ARIN."""
    from netbox_rir_manager.backends.base import RIRDataError

    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    with pytest.raises(RIRDataError) as excinfo:
        ARINBackend(api_key="test-key").create_customer("NET-PARENT", {**CUSTOMER, "country": country})

    assert str(excinfo.value) == (
        f"Invalid Customer details for ARIN: iso3166_1.code2: {country.upper()} is not an ISO 3166-1 "
        "alpha-2 country code"
    )
    mock_api.net.from_handle.assert_not_called()
