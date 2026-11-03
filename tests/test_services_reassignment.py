from unittest.mock import patch

import pytest

from netbox_rir_manager.backends.arin import ARINBackend

NET = {"net_name": "CUST-192-0-2-0-28", "start_address": "192.0.2.0", "end_address": "192.0.2.15"}


@pytest.mark.django_db
@patch("netbox_rir_manager.backends.arin.Api")
def test_invalid_net_is_refused_before_the_customer_is_created(mock_api_class, rir_network, rir_user_key):
    """A net ARIN cannot accept must not leave an orphan customer at ARIN."""
    from netbox_rir_manager.models import RIRSyncLog
    from netbox_rir_manager.services.reassignment import ReassignmentDataError, submit_reassignment

    backend = ARINBackend(api_key="test-key")
    net = {"net_name": "CUST", "start_address": "not-an-address", "end_address": "192.0.2.15"}

    with (
        patch.object(backend, "create_customer") as create_customer,
        pytest.raises(ReassignmentDataError, match="start_address"),
    ):
        submit_reassignment(backend, rir_network, rir_user_key, net, customer={"customer_name": "Cust"})

    create_customer.assert_not_called()
    assert RIRSyncLog.objects.get(status="error").operation == "reassign"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kwargs, backend_method, detail",
    [
        pytest.param(
            {"customer": {"customer_name": "Cust"}},
            "create_customer",
            "Failed to create customer at ARIN.",
            id="simple-creates-customer",
        ),
        pytest.param({"org_handle": "ORG-X"}, "reassign_network", "Reassignment failed at ARIN.", id="detailed"),
    ],
)
@patch("netbox_rir_manager.backends.arin.Api")
def test_valid_net_passes_the_check_before_arin(
    mock_api_class, rir_network, rir_user_key, kwargs, backend_method, detail
):
    """A valid net, which has no customer handle yet for a simple reassignment, goes on to ARIN."""
    from netbox_rir_manager.services.reassignment import ReassignmentError, submit_reassignment

    backend = ARINBackend(api_key="test-key")

    with (
        patch.object(backend, backend_method, return_value=None) as called,
        pytest.raises(ReassignmentError, match=detail),
    ):
        submit_reassignment(backend, rir_network, rir_user_key, NET, **kwargs)

    called.assert_called_once()


@pytest.mark.django_db
@patch("netbox_rir_manager.backends.arin.Api")
def test_net_refused_at_submission_is_a_data_error(mock_api_class, rir_network, rir_user_key):
    """A refusal from reassign_network itself is reported like the check before it."""
    from netbox_rir_manager.backends.base import RIRDataError
    from netbox_rir_manager.models import RIRSyncLog
    from netbox_rir_manager.services.reassignment import ReassignmentDataError, submit_reassignment

    backend = ARINBackend(api_key="test-key")

    with (
        patch.object(backend, "reassign_network", side_effect=RIRDataError("Invalid Net details for ARIN: x")),
        pytest.raises(ReassignmentDataError, match="Invalid Net details for ARIN: x"),
    ):
        submit_reassignment(backend, rir_network, rir_user_key, NET, org_handle="ORG-X")

    assert RIRSyncLog.objects.get(status="error").operation == "reassign"
