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
    def test_scheduled_sync_groups_by_synced_by_key(self, mock_backend_class, rir_config, admin_user, rir_user_key):
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
        mock_backend_class.from_rir_config.assert_called_once_with(rir_config, api_key=rir_user_key.api_key)


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


@pytest.mark.django_db
class TestReassignJobPreFlight:
    """Tests for the pre-flight check in ReassignJob that detects existing ARIN reassignments."""

    @pytest.fixture
    def reassign_setup(self, rir_config, rir_user_key, rir, rir_organization):
        """Set up common objects for reassign tests.

        Creates a parent aggregate/network and a child prefix with a tenant
        linked to an RIROrganization (for the detailed reassignment path).
        """
        from ipam.models import Aggregate, Prefix
        from tenancy.models import Tenant

        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="10.0.0.0/20", rir=rir)
        parent = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-PARENT-20",
            net_name="PARENT-NET",
            aggregate=agg,
            auto_reassign=True,
        )
        tenant = Tenant.objects.create(name="Test Tenant", slug="test-tenant")
        rir_organization.tenant = tenant
        rir_organization.save()
        pfx = Prefix.objects.create(prefix="10.0.1.0/29", tenant=tenant)
        return {"agg": agg, "parent": parent, "prefix": pfx}

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_preflight_syncs_existing_reassignment(
        self, mock_backend_class, reassign_setup, rir_config, rir_user_key
    ):
        """When ARIN returns a different net than parent, job syncs and returns early."""
        from netbox_rir_manager.jobs import ReassignJob
        from netbox_rir_manager.models import RIRNetwork, RIRSyncLog

        mock_backend = MagicMock()
        mock_backend.find_net.return_value = {
            "handle": "NET-INTERMEDIATE-24",
            "net_name": "INTERMEDIATE-NET",
            "net_type": "RS",
            "org_handle": "",
        }
        mock_backend_class.from_rir_config.return_value = mock_backend

        job = MagicMock()
        job.data = {}
        runner = ReassignJob.__new__(ReassignJob)
        runner.job = job

        runner.run(
            prefix_id=reassign_setup["prefix"].pk,
            user_key_id=rir_user_key.pk,
        )

        # Should have synced the intermediate net, not called reassign
        assert job.data["status"] == "synced"
        assert "NET-INTERMEDIATE-24" in job.data["message"]
        mock_backend.reassign_network.assert_not_called()

        # RIRNetwork should be created for the intermediate net
        assert RIRNetwork.objects.filter(handle="NET-INTERMEDIATE-24").exists()
        net = RIRNetwork.objects.get(handle="NET-INTERMEDIATE-24")
        assert net.prefix == reassign_setup["prefix"]

        # Sync log should record skipped
        log = RIRSyncLog.objects.filter(
            object_handle="NET-INTERMEDIATE-24", status="skipped"
        ).first()
        assert log is not None
        assert "already reassigned" in log.message

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_preflight_proceeds_when_arin_returns_parent(
        self, mock_backend_class, reassign_setup, rir_config, rir_user_key
    ):
        """When ARIN returns the parent handle, pre-flight passes and reassignment proceeds."""
        from netbox_rir_manager.jobs import ReassignJob

        mock_backend = MagicMock()
        # find_net returns parent handle -- no intermediate reassignment
        mock_backend.find_net.return_value = {
            "handle": "NET-PARENT-20",
            "net_name": "PARENT-NET",
        }
        # Reassignment itself fails (we just need to verify it was attempted)
        mock_backend.reassign_network.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        job = MagicMock()
        job.data = {}
        runner = ReassignJob.__new__(ReassignJob)
        runner.job = job

        runner.run(
            prefix_id=reassign_setup["prefix"].pk,
            user_key_id=rir_user_key.pk,
        )

        # Pre-flight should NOT have short-circuited -- reassign was attempted
        mock_backend.reassign_network.assert_called_once()

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_preflight_proceeds_when_arin_returns_none(
        self, mock_backend_class, reassign_setup, rir_config, rir_user_key
    ):
        """When ARIN returns None for find_net, pre-flight passes and reassignment proceeds."""
        from netbox_rir_manager.jobs import ReassignJob

        mock_backend = MagicMock()
        mock_backend.find_net.return_value = None
        mock_backend.reassign_network.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        job = MagicMock()
        job.data = {}
        runner = ReassignJob.__new__(ReassignJob)
        runner.job = job

        runner.run(
            prefix_id=reassign_setup["prefix"].pk,
            user_key_id=rir_user_key.pk,
        )

        # Pre-flight should NOT have short-circuited
        mock_backend.reassign_network.assert_called_once()


@pytest.mark.django_db
class TestRemoveNetworkJob:
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_remove_success(self, mock_backend_class, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import RemoveNetworkJob
        from netbox_rir_manager.models import RIRNetwork, RIRSyncLog

        net = RIRNetwork.objects.create(
            rir_config=rir_config, handle="NET-REMOVE-1", net_name="REMOVE-NET"
        )

        mock_backend = MagicMock()
        mock_backend.remove_network.return_value = True
        mock_backend_class.from_rir_config.return_value = mock_backend

        job = MagicMock()
        job.data = {}
        runner = RemoveNetworkJob.__new__(RemoveNetworkJob)
        runner.job = job

        runner.run(network_id=net.pk, user_key_id=rir_user_key.pk)

        mock_backend.remove_network.assert_called_once_with("NET-REMOVE-1")
        assert job.data["status"] == "success"

        log = RIRSyncLog.objects.get(object_handle="NET-REMOVE-1", operation="remove")
        assert log.status == "success"
        assert "Removed" in log.message

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_remove_failure(self, mock_backend_class, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import RemoveNetworkJob
        from netbox_rir_manager.models import RIRNetwork, RIRSyncLog

        net = RIRNetwork.objects.create(
            rir_config=rir_config, handle="NET-RMFAIL-1", net_name="FAIL-NET"
        )

        mock_backend = MagicMock()
        mock_backend.remove_network.return_value = False
        mock_backend_class.from_rir_config.return_value = mock_backend

        job = MagicMock()
        job.data = {}
        runner = RemoveNetworkJob.__new__(RemoveNetworkJob)
        runner.job = job

        runner.run(network_id=net.pk, user_key_id=rir_user_key.pk)

        assert job.data["status"] == "error"
        assert job.data["message"] == "ARIN removal failed"

        log = RIRSyncLog.objects.get(object_handle="NET-RMFAIL-1", operation="remove")
        assert log.status == "error"
