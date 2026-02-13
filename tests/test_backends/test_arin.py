from unittest.mock import MagicMock, patch

from netbox_rir_manager.backends.arin import ARINBackend
from netbox_rir_manager.backends.base import RIRBackend


def test_arin_backend_is_rir_backend():
    assert issubclass(ARINBackend, RIRBackend)


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
def test_from_rir_config(mock_api_class):
    """from_rir_config should create a backend from an RIRConfig-like object."""
    rir_config = MagicMock()
    rir_config.api_url = "https://reg.ote.arin.net/"

    backend = ARINBackend.from_rir_config(rir_config, api_key="test-key")
    assert isinstance(backend, ARINBackend)
    mock_api_class.assert_called_once_with(api_key="test-key", base_url="https://reg.ote.arin.net/")


@patch("netbox_rir_manager.backends.arin.Api")
def test_from_rir_config_no_api_url(mock_api_class):
    """from_rir_config with empty api_url should not pass base_url."""
    rir_config = MagicMock()
    rir_config.api_url = ""

    backend = ARINBackend.from_rir_config(rir_config, api_key="test-key")
    assert isinstance(backend, ARINBackend)
    mock_api_class.assert_called_once_with(api_key="test-key")


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
    mock_poc.dict.return_value = {
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
    mock_poc.dict.return_value = {
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
    mock_org.dict.return_value = {
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
    mock_org.dict.return_value = {
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
    mock_net.dict.return_value = {
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
    mock_net.dict.return_value = {
        "handle": "NET-192-0-2-0-1",
        "net_name": "EXAMPLE-NET",
        "version": 4,
        "org_handle": "EXAMPLE-ARIN",
        "parent_net_handle": "",
        "net_blocks": [
            {"start_address": "192.0.2.0", "end_address": "192.0.2.255", "cidr_length": 24, "type": "A"}
        ],
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


# ------------------------------------------------------------------
# Helper to create a mock Error that passes isinstance checks
# ------------------------------------------------------------------


def _make_mock_error():
    """Create a MagicMock that passes ``isinstance(x, Error)``."""
    from netbox_rir_manager.backends import arin as arin_mod

    error_cls = arin_mod.Error
    mock_error = MagicMock(spec=error_cls)
    mock_error.__class__ = error_cls
    return mock_error


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
    mock_net.dict.return_value = dict(defaults)
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
    mock_ticket.dict.return_value = dict(ticket_data)

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
    """update_network should return None when the fetch returns an Error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = _make_mock_error()

    backend = ARINBackend(api_key="test-key")
    result = backend.update_network("NET-BAD", {"net_name": "X"})

    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_update_network_error_on_save(mock_api_class):
    """update_network should return None when save returns an Error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_net = _make_mock_net()
    mock_net.save.return_value = _make_mock_error()
    mock_api.net.from_handle.return_value = mock_net

    backend = ARINBackend(api_key="test-key")
    result = backend.update_network("NET-TEST", {"net_name": "X"})

    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_update_network_none_on_fetch(mock_api_class):
    """update_network should return None when the fetch returns None (connection failure)."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.update_network("NET-BAD", {})

    assert result is None


# ------------------------------------------------------------------
# reassign_network tests
# ------------------------------------------------------------------


@patch("regrws.models.Net", new_callable=MagicMock)
@patch("netbox_rir_manager.backends.arin.Api")
def test_reassign_network_success(mock_api_class, mock_net_class):
    """reassign_network should return ticket info on success."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_parent = _make_mock_net(handle="NET-PARENT")
    mock_ticket_request = _make_mock_ticket_request(ticket_no="TKT-001")

    mock_api.net.from_handle.return_value = mock_parent
    mock_api.net.reassign.return_value = mock_ticket_request

    backend = ARINBackend(api_key="test-key")
    result = backend.reassign_network("NET-PARENT", {"net_name": "child"})

    assert result is not None
    assert result["ticket_number"] == "TKT-001"
    assert result["ticket_status"] == "PENDING_REVIEW"
    assert result["ticket_type"] == "IPV4_SIMPLE_REASSIGN"
    assert result["created_date"] == "2026-02-05"


@patch("regrws.models.Net", new_callable=MagicMock)
@patch("netbox_rir_manager.backends.arin.Api")
def test_reassign_network_with_net_in_response(mock_api_class, mock_net_class):
    """reassign_network should include net dict when ticket_request has a net."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_parent = _make_mock_net(handle="NET-PARENT")
    child_net = _make_mock_net(handle="NET-CHILD", net_name="CHILD-NET")
    mock_ticket_request = _make_mock_ticket_request(ticket_no="TKT-002", net=child_net)

    mock_api.net.from_handle.return_value = mock_parent
    mock_api.net.reassign.return_value = mock_ticket_request

    backend = ARINBackend(api_key="test-key")
    result = backend.reassign_network("NET-PARENT", {"net_name": "child"})

    assert result is not None
    assert "net" in result
    assert result["net"]["handle"] == "NET-CHILD"


@patch("netbox_rir_manager.backends.arin.Api")
def test_reassign_network_error_on_parent_fetch(mock_api_class):
    """reassign_network should return None when parent fetch fails."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = _make_mock_error()

    backend = ARINBackend(api_key="test-key")
    result = backend.reassign_network("NET-BAD", {"net_name": "child"})

    assert result is None


@patch("regrws.models.Net", new_callable=MagicMock)
@patch("netbox_rir_manager.backends.arin.Api")
def test_reassign_network_error_on_reassign(mock_api_class, mock_net_class):
    """reassign_network should return None when reassign call returns Error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_parent = _make_mock_net(handle="NET-PARENT")
    mock_api.net.from_handle.return_value = mock_parent
    mock_api.net.reassign.return_value = _make_mock_error()

    backend = ARINBackend(api_key="test-key")
    result = backend.reassign_network("NET-PARENT", {"net_name": "child"})

    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_reassign_network_none_on_parent_fetch(mock_api_class):
    """reassign_network should return None when parent fetch returns None."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.reassign_network("NET-BAD", {"net_name": "child"})

    assert result is None


# ------------------------------------------------------------------
# reallocate_network tests
# ------------------------------------------------------------------


@patch("regrws.models.Net", new_callable=MagicMock)
@patch("netbox_rir_manager.backends.arin.Api")
def test_reallocate_network_success(mock_api_class, mock_net_class):
    """reallocate_network should return ticket info on success."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_parent = _make_mock_net(handle="NET-PARENT")
    mock_ticket_request = _make_mock_ticket_request(ticket_no="TKT-010")

    mock_api.net.from_handle.return_value = mock_parent
    mock_api.net.reallocate.return_value = mock_ticket_request

    backend = ARINBackend(api_key="test-key")
    result = backend.reallocate_network("NET-PARENT", {"net_name": "sub-alloc"})

    assert result is not None
    assert result["ticket_number"] == "TKT-010"
    assert result["ticket_status"] == "PENDING_REVIEW"


@patch("netbox_rir_manager.backends.arin.Api")
def test_reallocate_network_error_on_parent_fetch(mock_api_class):
    """reallocate_network should return None when parent fetch fails."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = _make_mock_error()

    backend = ARINBackend(api_key="test-key")
    result = backend.reallocate_network("NET-BAD", {"net_name": "sub-alloc"})

    assert result is None


@patch("regrws.models.Net", new_callable=MagicMock)
@patch("netbox_rir_manager.backends.arin.Api")
def test_reallocate_network_error_on_reallocate(mock_api_class, mock_net_class):
    """reallocate_network should return None when reallocate call returns Error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_parent = _make_mock_net(handle="NET-PARENT")
    mock_api.net.from_handle.return_value = mock_parent
    mock_api.net.reallocate.return_value = _make_mock_error()

    backend = ARINBackend(api_key="test-key")
    result = backend.reallocate_network("NET-PARENT", {"net_name": "sub-alloc"})

    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_reallocate_network_none_on_parent_fetch(mock_api_class):
    """reallocate_network should return None when parent fetch returns None."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.reallocate_network("NET-BAD", {"net_name": "sub-alloc"})

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
def test_remove_network_error_on_fetch(mock_api_class):
    """remove_network should return False when the fetch returns an Error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = _make_mock_error()

    backend = ARINBackend(api_key="test-key")
    result = backend.remove_network("NET-BAD")

    assert result is False


@patch("netbox_rir_manager.backends.arin.Api")
def test_remove_network_error_on_remove(mock_api_class):
    """remove_network should return False when the remove call returns an Error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_net = _make_mock_net(handle="NET-TEST")
    mock_api.net.from_handle.return_value = mock_net
    mock_api.net.remove.return_value = _make_mock_error()

    backend = ARINBackend(api_key="test-key")
    result = backend.remove_network("NET-TEST")

    assert result is False


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
def test_delete_network_error_on_fetch(mock_api_class):
    """delete_network should return None when the fetch returns an Error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = _make_mock_error()

    backend = ARINBackend(api_key="test-key")
    result = backend.delete_network("NET-BAD")

    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_delete_network_error_on_delete(mock_api_class):
    """delete_network should return None when delete returns an Error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_net = _make_mock_net(handle="NET-TEST")
    mock_net.delete.return_value = _make_mock_error()
    mock_api.net.from_handle.return_value = mock_net

    backend = ARINBackend(api_key="test-key")
    result = backend.delete_network("NET-TEST")

    assert result is None


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
    mock_customer.dict.return_value = {
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
    mock_api.customer.from_handle.return_value = _make_mock_error()

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
    mock_customer.dict.return_value = {
        "handle": "C-TEST",
        "customer_name": "Test Customer",
        "parent_org_handle": "ORG-TEST",
    }

    mock_api.net.from_handle.return_value = mock_parent
    mock_api.customer.create_for_net.return_value = mock_customer

    backend = ARINBackend(api_key="test-key")
    result = backend.create_customer("NET-PARENT", {"customer_name": "Test Customer"})

    assert result is not None
    assert result["handle"] == "C-TEST"
    assert result["customer_name"] == "Test Customer"
    assert result["parent_org_handle"] == "ORG-TEST"
    assert "raw_data" in result


@patch("netbox_rir_manager.backends.arin.Api")
def test_create_customer_error_on_parent_fetch(mock_api_class):
    """create_customer should return None when parent fetch fails."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = _make_mock_error()

    backend = ARINBackend(api_key="test-key")
    result = backend.create_customer("NET-BAD", {"customer_name": "Test"})

    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_create_customer_error_on_create(mock_api_class):
    """create_customer should return None when create_for_net returns Error."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api

    mock_parent = _make_mock_net(handle="NET-PARENT")
    mock_api.net.from_handle.return_value = mock_parent
    mock_api.customer.create_for_net.return_value = _make_mock_error()

    backend = ARINBackend(api_key="test-key")
    result = backend.create_customer("NET-PARENT", {"customer_name": "Test"})

    assert result is None


@patch("netbox_rir_manager.backends.arin.Api")
def test_create_customer_none_on_parent_fetch(mock_api_class):
    """create_customer should return None when parent fetch returns None."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.net.from_handle.return_value = None

    backend = ARINBackend(api_key="test-key")
    result = backend.create_customer("NET-BAD", {"customer_name": "Test"})

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
    result = backend.create_customer("NET-PARENT", {"customer_name": "Test"})

    assert result is None
