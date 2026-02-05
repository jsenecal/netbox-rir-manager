from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.django_db
class TestRIRSyncJob:
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_creates_org_and_log(self, mock_backend_class, rir_config):
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIROrganization, RIRSyncLog

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = {
            "handle": "TESTORG-ARIN",
            "name": "Test Org",
            "street_address": "",
            "city": "Anytown",
            "state_province": "VA",
            "postal_code": "12345",
            "country": "US",
            "raw_data": {},
        }
        mock_backend_class.from_rir_config.return_value = mock_backend

        logs = sync_rir_config(rir_config, resource_types=["organizations"])

        assert len(logs) == 1
        assert logs[0].status == "success"
        assert RIROrganization.objects.filter(handle="TESTORG-ARIN").exists()
        assert RIRSyncLog.objects.filter(rir_config=rir_config).count() == 1

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_error_creates_error_log(self, mock_backend_class, rir_config):
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRSyncLog

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        logs = sync_rir_config(rir_config, resource_types=["organizations"])

        assert len(logs) == 1
        assert logs[0].status == "error"
        assert RIRSyncLog.objects.filter(rir_config=rir_config, status="error").count() == 1

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_updates_last_sync(self, mock_backend_class, rir_config):
        from netbox_rir_manager.jobs import sync_rir_config

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        assert rir_config.last_sync is None
        sync_rir_config(rir_config, resource_types=["organizations"])

        rir_config.refresh_from_db()
        assert rir_config.last_sync is not None
