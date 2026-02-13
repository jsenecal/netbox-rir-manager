from unittest.mock import MagicMock, patch

import pytest


def make_runner(cls):
    """Create a job runner with mocked job and logger (bypasses __init__)."""
    runner = cls.__new__(cls)
    runner.job = MagicMock()
    runner.job.data = {}
    runner.logger = MagicMock()
    return runner


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

        runner = make_runner(ScheduledRIRSyncJob)

        runner.run()

        assert RIROrganization.objects.filter(handle="SCHED-ARIN").exists()

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_skips_inactive_configs(self, mock_backend_class, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        rir_config.is_active = False
        rir_config.save()

        runner = make_runner(ScheduledRIRSyncJob)

        runner.run()

        mock_backend_class.from_rir_config.assert_not_called()

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_skips_config_without_keys(self, mock_backend_class, rir_config):
        """Config without any RIRUserKey entries should be skipped."""
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        runner = make_runner(ScheduledRIRSyncJob)

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

        runner = make_runner(ScheduledRIRSyncJob)

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

        logs, agg_nets = sync_rir_config(rir_config, api_key="test-key", resource_types=["organizations"])

        assert len(logs) == 1
        assert logs[0].status == "success"
        assert agg_nets == []
        assert RIROrganization.objects.filter(handle="TESTORG-ARIN").exists()
        assert RIRSyncLog.objects.filter(rir_config=rir_config).count() == 1

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_error_creates_error_log(self, mock_backend_class, rir_config):
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRSyncLog

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        logs, agg_nets = sync_rir_config(rir_config, api_key="test-key", resource_types=["organizations"])

        assert len(logs) == 1
        assert logs[0].status == "error"
        assert agg_nets == []
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

        logs, agg_nets = sync_rir_config(rir_config, api_key="test-key", resource_types=["networks"])

        net = RIRNetwork.objects.get(handle="NET-192-0-2-0-1")
        assert net.net_name == "EXAMPLE-NET"
        assert net.aggregate is not None
        assert str(net.aggregate.prefix) == "192.0.2.0/24"
        assert len(agg_nets) == 1

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

        runner = make_runner(SyncRIRConfigJob)
        runner.job.object_id = rir_config.pk

        runner.run(user_id=admin_user.pk)

        # Verify the job data was updated
        assert "rir_config" in runner.job.data

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_returns_agg_nets(self, mock_backend_class, rir_config, rir):
        """sync_rir_config returns (logs, agg_nets) with aggregate/network pairs."""
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="10.0.0.0/8", rir=rir)

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = None
        mock_backend.find_net.return_value = {
            "handle": "NET-10-0-0-0-1",
            "net_name": "BIG-NET",
            "version": 4,
            "org_handle": "",
            "parent_net_handle": "",
            "net_blocks": [],
            "raw_data": {},
        }
        mock_backend_class.from_rir_config.return_value = mock_backend

        logs, agg_nets = sync_rir_config(rir_config, api_key="test-key", resource_types=["networks"])

        assert len(logs) == 1
        assert len(agg_nets) == 1
        returned_agg, returned_net = agg_nets[0]
        assert returned_agg.pk == agg.pk
        assert isinstance(returned_net, RIRNetwork)
        assert returned_net.handle == "NET-10-0-0-0-1"


@pytest.mark.django_db
class TestSyncPrefixesJob:
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_discovers_child_prefixes(self, mock_backend_class, rir_config, rir_user_key, rir):
        """SyncPrefixesJob discovers and syncs child prefix networks."""
        from ipam.models import Aggregate, Prefix

        from netbox_rir_manager.jobs import SyncPrefixesJob
        from netbox_rir_manager.models import RIRNetwork, RIRSyncLog

        agg = Aggregate.objects.create(prefix="10.0.0.0/20", rir=rir)
        parent_net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-PARENT-20",
            net_name="PARENT-NET",
            aggregate=agg,
        )
        Prefix.objects.create(prefix="10.0.1.0/24")
        Prefix.objects.create(prefix="10.0.2.0/24")

        call_count = 0

        def find_net_side_effect(start, end):
            nonlocal call_count
            call_count += 1
            if start == "10.0.1.0":
                return {
                    "handle": "NET-CHILD-1",
                    "net_name": "CHILD-NET-1",
                    "version": 4,
                    "org_handle": "",
                    "parent_net_handle": "NET-PARENT-20",
                    "net_blocks": [],
                    "raw_data": {},
                }
            elif start == "10.0.2.0":
                # Returns parent handle -- should be skipped
                return {
                    "handle": "NET-PARENT-20",
                    "net_name": "PARENT-NET",
                    "version": 4,
                    "org_handle": "",
                    "parent_net_handle": "",
                    "net_blocks": [],
                    "raw_data": {},
                }
            return None

        mock_backend = MagicMock()
        mock_backend.find_net.side_effect = find_net_side_effect
        mock_backend_class.from_rir_config.return_value = mock_backend

        runner = make_runner(SyncPrefixesJob)

        runner.run(
            aggregate_id=agg.pk,
            parent_handle=parent_net.handle,
            user_key_id=rir_user_key.pk,
        )

        # Child net should be created
        assert RIRNetwork.objects.filter(handle="NET-CHILD-1").exists()
        # Parent-returning prefix should be skipped -- no duplicate
        assert RIRNetwork.objects.filter(handle="NET-PARENT-20").count() == 1
        # Sync log for the child
        assert RIRSyncLog.objects.filter(object_handle="NET-CHILD-1").exists()

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_logs_progress(self, mock_backend_class, rir_config, rir_user_key, rir):
        """SyncPrefixesJob logs progress via self.logger."""
        from ipam.models import Aggregate, Prefix

        from netbox_rir_manager.jobs import SyncPrefixesJob
        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="10.0.0.0/20", rir=rir)
        RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-PARENT-20",
            net_name="PARENT-NET",
            aggregate=agg,
        )
        Prefix.objects.create(prefix="10.0.1.0/24")

        mock_backend = MagicMock()
        mock_backend.find_net.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        runner = make_runner(SyncPrefixesJob)

        runner.run(
            aggregate_id=agg.pk,
            parent_handle="NET-PARENT-20",
            user_key_id=rir_user_key.pk,
        )

        # Should have logged the scanning message
        runner.logger.info.assert_called()
        first_info_call = runner.logger.info.call_args_list[0]
        assert "Scanning" in first_info_call[0][0]


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

        runner = make_runner(ReassignJob)

        runner.run(
            prefix_id=reassign_setup["prefix"].pk,
            user_key_id=rir_user_key.pk,
        )

        # Should have synced the intermediate net, not called reassign
        assert runner.job.data["status"] == "synced"
        assert "NET-INTERMEDIATE-24" in runner.job.data["message"]
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

        runner = make_runner(ReassignJob)

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

        runner = make_runner(ReassignJob)

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

        runner = make_runner(RemoveNetworkJob)

        runner.run(network_id=net.pk, user_key_id=rir_user_key.pk)

        mock_backend.remove_network.assert_called_once_with("NET-REMOVE-1")
        assert runner.job.data["status"] == "success"

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

        runner = make_runner(RemoveNetworkJob)

        runner.run(network_id=net.pk, user_key_id=rir_user_key.pk)

        assert runner.job.data["status"] == "error"
        assert runner.job.data["message"] == "ARIN removal failed"

        log = RIRSyncLog.objects.get(object_handle="NET-RMFAIL-1", operation="remove")
        assert log.status == "error"
