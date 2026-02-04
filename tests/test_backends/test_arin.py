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
def test_from_account(mock_api_class):
    """from_account should create a backend from an RIRAccount-like object."""
    account = MagicMock()
    account.api_key = "account-key"
    account.api_url = "https://reg.ote.arin.net/"

    backend = ARINBackend.from_account(account)
    assert isinstance(backend, ARINBackend)
    mock_api_class.assert_called_once_with(api_key="account-key", base_url="https://reg.ote.arin.net/")


@patch("netbox_rir_manager.backends.arin.Api")
def test_from_account_no_api_url(mock_api_class):
    """from_account with empty api_url should not pass base_url."""
    account = MagicMock()
    account.api_key = "account-key"
    account.api_url = ""

    backend = ARINBackend.from_account(account)
    assert isinstance(backend, ARINBackend)
    mock_api_class.assert_called_once_with(api_key="account-key")


@patch("netbox_rir_manager.backends.arin.Api")
def test_authenticate_success(mock_api_class):
    mock_api = MagicMock()
    mock_org = MagicMock()  # Not an Error instance
    mock_api.org.from_handle.return_value = mock_org
    mock_api_class.return_value = mock_api

    account = MagicMock()
    account.org_handle = "EXAMPLE-ARIN"

    backend = ARINBackend(api_key="test-key")
    assert backend.authenticate(account) is True
    mock_api.org.from_handle.assert_called_once_with("EXAMPLE-ARIN")


@patch("netbox_rir_manager.backends.arin.Api")
def test_authenticate_no_org_handle(mock_api_class):
    account = MagicMock()
    account.org_handle = ""

    backend = ARINBackend(api_key="test-key")
    assert backend.authenticate(account) is False


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

    account = MagicMock()
    account.org_handle = "BADHANDLE"

    backend = ARINBackend(api_key="test-key")
    with patch.object(arin_mod, "Error", real_error_class):
        assert backend.authenticate(account) is False


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
    assert result["net_blocks"] == []
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
    account = MagicMock()
    backend = ARINBackend(api_key="test-key")
    assert backend.sync_resources(account) == []


@patch("netbox_rir_manager.backends.arin.Api")
def test_backend_registered(mock_api_class):
    """ARINBackend should be auto-registered in BACKENDS dict."""
    from netbox_rir_manager.backends import BACKENDS, get_backend

    assert "ARIN" in BACKENDS
    assert get_backend("ARIN") is ARINBackend
