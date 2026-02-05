from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.django_db
class TestScheduledSyncJob:
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_all_active_configs(self, mock_backend_class, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob
        from netbox_rir_manager.models import RIROrganization

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = {
            "handle": "SCHED-ARIN",
            "name": "Scheduled Org",
            "street_address": "",
            "city": "",
            "state_province": "",
            "postal_code": "",
            "country": "",
            "poc_links": [],
            "raw_data": {},
        }
        mock_backend.find_net.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        job = MagicMock()
        job.data = {}
        runner = ScheduledRIRSyncJob.__new__(ScheduledRIRSyncJob)
        runner.job = job

        runner.run()

        assert RIROrganization.objects.filter(handle="SCHED-ARIN").exists()

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_skips_inactive_configs(self, mock_backend_class, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        rir_config.is_active = False
        rir_config.save()

        job = MagicMock()
        job.data = {}
        runner = ScheduledRIRSyncJob.__new__(ScheduledRIRSyncJob)
        runner.job = job

        runner.run()

        mock_backend_class.from_rir_config.assert_not_called()

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_skips_config_without_keys(self, mock_backend_class, rir_config):
        """Config without any RIRUserKey entries should be skipped."""
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        job = MagicMock()
        job.data = {}
        runner = ScheduledRIRSyncJob.__new__(ScheduledRIRSyncJob)
        runner.job = job

        runner.run()

        mock_backend_class.from_rir_config.assert_not_called()

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_groups_by_synced_by_key(
        self, mock_backend_class, rir_config, admin_user, rir_user_key
    ):
        """Objects with synced_by set should be refreshed using the same key."""
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob
        from netbox_rir_manager.models import RIROrganization

        # Create an org that was synced_by this user key
        RIROrganization.objects.create(
            rir_config=rir_config,
            handle="GROUPED-ARIN",
            name="Grouped Org",
            synced_by=rir_user_key,
        )

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = {
            "handle": "GROUPED-ARIN",
            "name": "Grouped Org Updated",
            "street_address": "",
            "city": "",
            "state_province": "",
            "postal_code": "",
            "country": "",
            "poc_links": [],
            "raw_data": {},
        }
        mock_backend.find_net.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        job = MagicMock()
        job.data = {}
        runner = ScheduledRIRSyncJob.__new__(ScheduledRIRSyncJob)
        runner.job = job

        runner.run()

        # Verify the backend was created with the correct key
        mock_backend_class.from_rir_config.assert_called_once_with(
            rir_config, api_key=rir_user_key.api_key
        )


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
            "poc_links": [],
            "raw_data": {},
        }
        mock_backend_class.from_rir_config.return_value = mock_backend

        logs = sync_rir_config(rir_config, api_key="test-key", resource_types=["organizations"])

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

        logs = sync_rir_config(rir_config, api_key="test-key", resource_types=["organizations"])

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
        sync_rir_config(rir_config, api_key="test-key", resource_types=["organizations"])

        rir_config.refresh_from_db()
        assert rir_config.last_sync is not None

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_contacts_from_org(self, mock_backend_class, rir_config):
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRContact, RIROrganization

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = {
            "handle": "TESTORG-ARIN",
            "name": "Test Org",
            "street_address": "",
            "city": "Anytown",
            "state_province": "VA",
            "postal_code": "12345",
            "country": "US",
            "poc_links": [{"handle": "JD123-ARIN", "function": "AD"}],
            "raw_data": {},
        }
        mock_backend.get_poc.return_value = {
            "handle": "JD123-ARIN",
            "contact_type": "PERSON",
            "first_name": "John",
            "last_name": "Doe",
            "company_name": "Test Org",
            "email": "john@example.com",
            "phone": "",
            "raw_data": {},
        }
        mock_backend_class.from_rir_config.return_value = mock_backend

        sync_rir_config(rir_config, api_key="test-key", resource_types=["organizations", "contacts"])

        assert RIROrganization.objects.filter(handle="TESTORG-ARIN").exists()
        assert RIRContact.objects.filter(handle="JD123-ARIN").exists()
        contact = RIRContact.objects.get(handle="JD123-ARIN")
        assert contact.first_name == "John"
        assert contact.last_name == "Doe"

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_networks_from_ipam(self, mock_backend_class, rir_config, rir):
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRNetwork

        Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = None  # no org to sync
        mock_backend.find_net.return_value = {
            "handle": "NET-192-0-2-0-1",
            "net_name": "EXAMPLE-NET",
            "version": 4,
            "org_handle": "",
            "parent_net_handle": "",
            "net_blocks": [
                {"start_address": "192.0.2.0", "end_address": "192.0.2.255", "cidr_length": 24, "type": "DS"}
            ],
            "raw_data": {},
        }
        mock_backend_class.from_rir_config.return_value = mock_backend

        sync_rir_config(rir_config, api_key="test-key", resource_types=["networks"])

        net = RIRNetwork.objects.get(handle="NET-192-0-2-0-1")
        assert net.net_name == "EXAMPLE-NET"
        assert net.aggregate is not None
        assert str(net.aggregate.prefix) == "192.0.2.0/24"

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_sets_synced_by(self, mock_backend_class, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIROrganization

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = {
            "handle": "SYNCBY-ARIN",
            "name": "Sync By Org",
            "street_address": "",
            "city": "",
            "state_province": "",
            "postal_code": "",
            "country": "",
            "poc_links": [],
            "raw_data": {},
        }
        mock_backend.find_net.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        sync_rir_config(rir_config, api_key="test-key", user_key=rir_user_key)

        org = RIROrganization.objects.get(handle="SYNCBY-ARIN")
        assert org.synced_by == rir_user_key

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_job_runner(self, mock_backend_class, rir_config, admin_user):
        from netbox_rir_manager.jobs import SyncRIRConfigJob
        from netbox_rir_manager.models import RIRUserKey

        RIRUserKey.objects.create(user=admin_user, rir_config=rir_config, api_key="job-key")

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = None
        mock_backend.find_net.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        # Create a mock job object
        job = MagicMock()
        job.object_id = rir_config.pk
        job.data = {}

        runner = SyncRIRConfigJob.__new__(SyncRIRConfigJob)
        runner.job = job

        runner.run(user_id=admin_user.pk)

        # Verify the job data was updated
        assert "rir_config" in job.data
