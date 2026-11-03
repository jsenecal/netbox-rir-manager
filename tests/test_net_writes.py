from unittest.mock import MagicMock

import pytest


@pytest.mark.django_db
class TestSubmitNetRemove:
    def test_success_is_logged(self, rir_network):
        from netbox_rir_manager.models import RIRSyncLog
        from netbox_rir_manager.services.net_writes import submit_net_remove

        backend = MagicMock()
        backend.remove_network.return_value = True

        submit_net_remove(backend, rir_network)

        backend.remove_network.assert_called_once_with(rir_network.handle)
        log = RIRSyncLog.objects.get(operation="remove")
        assert (log.status, log.object_handle, log.message) == (
            "success",
            rir_network.handle,
            f"Removed network {rir_network.handle} from ARIN",
        )

    def test_failure_is_logged_then_raised(self, rir_network):
        from netbox_rir_manager.models import RIRSyncLog
        from netbox_rir_manager.services.arin_results import ARINWriteError
        from netbox_rir_manager.services.net_writes import submit_net_remove

        backend = MagicMock()
        backend.remove_network.return_value = False

        with pytest.raises(ARINWriteError, match=r"^Failed to remove network from ARIN\.$"):
            submit_net_remove(backend, rir_network)

        log = RIRSyncLog.objects.get(operation="remove")
        assert (log.status, log.message) == ("error", "Failed to remove network from ARIN.")
