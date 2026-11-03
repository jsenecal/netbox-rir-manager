from unittest.mock import MagicMock, patch

import pytest

from tests.arin_payloads import EXISTING_TICKET, NOT_FOUND, immediate_result, ticket_result


def make_runner(cls):
    """Create a job runner with mocked job and logger (bypasses __init__)."""
    runner = cls.__new__(cls)
    runner.job = MagicMock()
    runner.job.data = {}
    runner.logger = MagicMock()
    return runner


def wire_org(mock_backend_class, handle, name):
    """Make ARIN return one organization with no POCs and no nets."""
    mock_backend = MagicMock()
    mock_backend.get_organization.return_value = {
        "handle": handle,
        "name": name,
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
    return mock_backend


def wire_owned_net(mock_backend_class, org_handle, handle="NET-10-0-0-0-1"):
    """Make every ARIN lookup return one net registered to org_handle, with no organization."""
    mock_backend = MagicMock()
    mock_backend.get_organization.return_value = None
    mock_backend.find_net.return_value = {
        "handle": handle,
        "net_name": "BIG-NET",
        "version": 4,
        "org_handle": org_handle,
        "parent_net_handle": "",
        "net_blocks": [],
        "raw_data": {},
    }
    mock_backend_class.from_rir_config.return_value = mock_backend
    return mock_backend


@pytest.mark.django_db
class TestScheduledSyncJob:
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_all_active_configs(self, mock_backend_class, rir_config, default_key):
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob
        from netbox_rir_manager.models import RIROrganization

        wire_org(mock_backend_class, "SCHED-ARIN", "Scheduled Org")

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
    def test_scheduled_sync_uses_only_default_key(self, mock_backend_class, rir_config, default_key, operator_key):
        """Scheduled sync has no acting user: it syncs once with the default key, never other users' keys."""
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = None
        mock_backend.find_net.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        make_runner(ScheduledRIRSyncJob).run()

        mock_backend_class.from_rir_config.assert_called_once_with(rir_config, api_key=default_key.api_key)

    @patch("netbox_rir_manager.jobs.SyncPrefixesJob")
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_queues_prefix_discovery_with_default_key(
        self, mock_backend_class, mock_prefix_job, rir_config, default_key, operator_key, rir
    ):
        """Like the manual sync, each owned aggregate gets one prefix sync, run with the default key as its owner."""
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        agg = Aggregate.objects.create(prefix="10.0.0.0/8", rir=rir)
        wire_owned_net(mock_backend_class, rir_config.org_handle)

        make_runner(ScheduledRIRSyncJob).run()

        mock_prefix_job.enqueue.assert_called_once_with(
            instance=rir_config,
            user=default_key.user,
            aggregate_id=agg.pk,
            parent_handle="NET-10-0-0-0-1",
            user_key_id=default_key.pk,
        )

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_skips_config_without_default_key(self, mock_backend_class, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        make_runner(ScheduledRIRSyncJob).run()

        mock_backend_class.from_rir_config.assert_not_called()

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_skips_config_whose_default_key_owner_is_deactivated(
        self, mock_backend_class, rir_config, default_key
    ):
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        default_key.user.is_active = False
        default_key.user.save()

        runner = make_runner(ScheduledRIRSyncJob)
        runner.run()

        mock_backend_class.from_rir_config.assert_not_called()
        warning = runner.logger.warning.call_args[0][0]
        assert "deactivated user" in warning


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
    def test_sync_contacts_poc_in_several_roles_synced_once(self, mock_backend_class, rir_config):
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIROrganization, RIRSyncLog

        poc_links = [
            {"handle": "NOC11106-ARIN", "function": "N"},
            {"handle": "NOC11106-ARIN", "function": "T"},
            {"handle": "JD123-ARIN", "function": "AD"},
        ]
        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = {
            "handle": "TESTORG-ARIN",
            "name": "Test Org",
            "poc_links": poc_links,
            "raw_data": {},
        }
        mock_backend.get_poc.side_effect = lambda handle: {
            "handle": handle,
            "contact_type": "ROLE",
            "last_name": handle,
            "raw_data": {},
        }
        mock_backend_class.from_rir_config.return_value = mock_backend

        sync_rir_config(rir_config, api_key="test-key", resource_types=["organizations", "contacts"])

        fetched = [c.args[0] for c in mock_backend.get_poc.call_args_list]
        assert fetched == ["NOC11106-ARIN", "JD123-ARIN"]
        assert (
            RIRSyncLog.objects.filter(object_type="contact", object_handle="NOC11106-ARIN", status="success").count()
            == 1
        )
        assert RIROrganization.objects.get(handle="TESTORG-ARIN").raw_data["poc_links"] == poc_links

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
            "org_handle": "TESTORG-ARIN",
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

        wire_org(mock_backend_class, "SYNCBY-ARIN", "Sync By Org")

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
        runner.job.user = admin_user

        runner.run()

        # Verify the job data was updated
        assert "rir_config" in runner.job.data
        mock_backend_class.from_rir_config.assert_called_once_with(rir_config, api_key="job-key")

    @patch("netbox_rir_manager.jobs.SyncPrefixesJob")
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_job_queues_prefix_discovery_with_users_key(
        self, mock_backend_class, mock_prefix_job, rir_config, default_key, operator_key, rir
    ):
        """A manual sync queues one prefix sync per owned aggregate, with the requesting user's own key."""
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import SyncRIRConfigJob

        agg = Aggregate.objects.create(prefix="10.0.0.0/8", rir=rir)
        wire_owned_net(mock_backend_class, rir_config.org_handle)

        runner = make_runner(SyncRIRConfigJob)
        runner.job.object_id = rir_config.pk
        runner.job.user = operator_key.user
        runner.run()

        mock_prefix_job.enqueue.assert_called_once_with(
            instance=rir_config,
            user=operator_key.user,
            aggregate_id=agg.pk,
            parent_handle="NET-10-0-0-0-1",
            user_key_id=operator_key.pk,
        )

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_job_without_users_key_does_nothing(self, mock_backend_class, rir_config, default_key, make_user):
        """A user-triggered sync never borrows the default key."""
        from netbox_rir_manager.jobs import SyncRIRConfigJob

        runner = make_runner(SyncRIRConfigJob)
        runner.job.object_id = rir_config.pk
        runner.job.user = make_user("keyless")

        runner.run()

        mock_backend_class.from_rir_config.assert_not_called()
        assert runner.job.data["status"] == "error"

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_returns_agg_nets(self, mock_backend_class, rir_config, rir):
        """sync_rir_config returns (logs, agg_nets) with aggregate/network pairs."""
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="10.0.0.0/8", rir=rir)
        wire_owned_net(mock_backend_class, rir_config.org_handle)

        logs, agg_nets = sync_rir_config(rir_config, api_key="test-key", resource_types=["networks"])

        assert len(logs) == 1
        assert len(agg_nets) == 1
        returned_agg, returned_net = agg_nets[0]
        assert returned_agg.pk == agg.pk
        assert isinstance(returned_net, RIRNetwork)
        assert returned_net.handle == "NET-10-0-0-0-1"

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_walks_up_to_net_owned_by_config_org(self, mock_backend_class, rir_config, rir):
        """When the most specific net is a child, the aggregate links to our parent net instead."""
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)

        mock_backend = MagicMock()
        mock_backend.get_organization.return_value = None
        mock_backend.find_net.return_value = {
            "handle": "NET-CHILD-1",
            "net_name": "CHILD-NET",
            "org_handle": "OTHER-ARIN",
            "parent_net_handle": "NET-PARENT-1",
            "raw_data": {},
        }
        mock_backend.get_network.return_value = {
            "handle": "NET-PARENT-1",
            "net_name": "OUR-NET",
            "org_handle": "TESTORG-ARIN",
            "parent_net_handle": "NET-UPSTREAM-1",
            "raw_data": {},
        }
        mock_backend_class.from_rir_config.return_value = mock_backend

        logs, agg_nets = sync_rir_config(rir_config, api_key="test-key", resource_types=["networks"])

        mock_backend.get_network.assert_called_once_with("NET-PARENT-1")
        assert RIRNetwork.objects.get(handle="NET-PARENT-1").aggregate == agg
        assert not RIRNetwork.objects.filter(handle="NET-CHILD-1").exists()
        assert [net.handle for _agg, net in agg_nets] == ["NET-PARENT-1"]

    @pytest.mark.parametrize(
        "config_org, found, parent, expected_lookups, owner_in_message",
        [
            pytest.param(
                "TESTORG-ARIN",
                {"handle": "NET-CUST-1", "customer_handle": "C01234567", "parent_net_handle": "NET-THEIRS-1"},
                {"handle": "NET-THEIRS-1", "org_handle": "OTHER-ARIN", "parent_net_handle": ""},
                1,
                "C01234567",
                id="chain-owned-by-another-org",
            ),
            pytest.param(
                "TESTORG-ARIN",
                {"handle": "NET-A", "org_handle": "OTHER-ARIN", "parent_net_handle": "NET-B"},
                {"handle": "NET-B", "org_handle": "OTHER-ARIN", "parent_net_handle": "NET-A"},
                1,
                "OTHER-ARIN",
                id="parent-chain-cycle",
            ),
            pytest.param(
                "TESTORG-ARIN",
                {"handle": "NET-A", "org_handle": "OTHER-ARIN", "parent_net_handle": "NET-B"},
                None,
                1,
                "OTHER-ARIN",
                id="parent-net-unavailable",
            ),
            pytest.param(
                "",
                {"handle": "NET-A", "org_handle": "OTHER-ARIN", "parent_net_handle": "NET-B"},
                None,
                0,
                "OTHER-ARIN",
                id="config-without-org-handle",
            ),
            pytest.param("TESTORG-ARIN", None, None, 0, "", id="no-net-at-arin"),
        ],
    )
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_skips_aggregate_not_owned_by_config_org(
        self, mock_backend_class, rir_config, rir, config_org, found, parent, expected_lookups, owner_in_message
    ):
        """An aggregate whose net chain never reaches the config org is skipped and logged, not synced."""
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRNetwork

        rir_config.org_handle = config_org
        rir_config.save()
        Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)

        mock_backend = MagicMock()
        mock_backend.find_net.return_value = found
        mock_backend.get_network.return_value = parent
        mock_backend_class.from_rir_config.return_value = mock_backend

        logs, agg_nets = sync_rir_config(rir_config, api_key="test-key", resource_types=["networks"])

        assert agg_nets == []
        assert not RIRNetwork.objects.exists()
        mock_backend.get_customer.assert_not_called()
        assert [log.status for log in logs] == ["skipped"]
        assert owner_in_message in logs[0].message
        assert mock_backend.get_network.call_count == expected_lookups

    @pytest.mark.parametrize(
        "prefix, expected_range",
        [
            pytest.param("192.0.2.8/31", ("192.0.2.8", "192.0.2.9"), id="ipv4-31"),
            pytest.param("192.0.2.8/32", ("192.0.2.8", "192.0.2.8"), id="ipv4-32"),
        ],
    )
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_queries_last_address_of_host_aggregate(
        self, mock_backend_class, rir_config, rir, prefix, expected_range
    ):
        """A /31 or /32 aggregate is looked up by its real last address, not "None"."""
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import sync_rir_config

        agg = Aggregate.objects.create(prefix=prefix, rir=rir)

        mock_backend = MagicMock()
        mock_backend.find_net.return_value = {
            "handle": "NET-HOST-1",
            "net_name": "HOST-NET",
            "org_handle": "TESTORG-ARIN",
            "parent_net_handle": "",
            "raw_data": {},
        }
        mock_backend_class.from_rir_config.return_value = mock_backend

        _logs, agg_nets = sync_rir_config(rir_config, api_key="test-key", resource_types=["networks"])

        mock_backend.find_net.assert_called_once_with(*expected_range)
        assert [(a.pk, net.handle) for a, net in agg_nets] == [(agg.pk, "NET-HOST-1")]


@pytest.mark.django_db
class TestSyncPrefixesJob:
    @pytest.mark.parametrize(
        "prefix, expected_range",
        [
            pytest.param("10.0.1.8/31", ("10.0.1.8", "10.0.1.9"), id="ipv4-31"),
            pytest.param("10.0.1.8/32", ("10.0.1.8", "10.0.1.8"), id="ipv4-32"),
        ],
    )
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_discovers_host_prefix_reassignment(
        self, mock_backend_class, rir_user_key, prefix_under_parent, prefix, expected_range
    ):
        """/31 and /32 child prefixes are looked up by their real last address and synced."""
        from netbox_rir_manager.jobs import SyncPrefixesJob
        from netbox_rir_manager.models import RIRNetwork

        setup = prefix_under_parent("10.0.0.0/20", prefix, "NET-PARENT-20")

        mock_backend = MagicMock()
        mock_backend.find_net.return_value = {
            "handle": "NET-HOST-1",
            "net_name": "HOST-NET",
            "org_handle": "",
            "parent_net_handle": "NET-PARENT-20",
            "net_blocks": [],
            "raw_data": {},
        }
        mock_backend_class.from_rir_config.return_value = mock_backend

        make_runner(SyncPrefixesJob).run(
            aggregate_id=setup["agg"].pk, parent_handle=setup["parent"].handle, user_key_id=rir_user_key.pk
        )

        mock_backend.find_net.assert_called_once_with(*expected_range)
        assert RIRNetwork.objects.get(handle="NET-HOST-1").prefix == setup["prefix"]

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
    def test_discovers_customer_for_child_prefix(self, mock_backend_class, rir_config, rir_user_key, rir):
        """SyncPrefixesJob fetches and persists customers for child networks with customer_handle."""
        from ipam.models import Aggregate, Prefix

        from netbox_rir_manager.jobs import SyncPrefixesJob
        from netbox_rir_manager.models import RIRCustomer, RIRNetwork

        agg = Aggregate.objects.create(prefix="10.0.0.0/20", rir=rir)
        parent_net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-PARENT-20",
            net_name="PARENT-NET",
            aggregate=agg,
        )
        Prefix.objects.create(prefix="10.0.1.0/24")

        mock_backend = MagicMock()
        mock_backend.find_net.return_value = {
            "handle": "NET-CHILD-1",
            "net_name": "CHILD-NET-1",
            "version": 4,
            "customer_handle": "C09999999",
            "org_handle": None,
            "parent_net_handle": "NET-PARENT-20",
            "net_blocks": [],
            "raw_data": {},
        }
        mock_backend.get_customer.return_value = {
            "handle": "C09999999",
            "customer_name": "Child Customer",
            "street_address": "",
            "city": "Springfield",
            "state_province": "IL",
            "postal_code": "62701",
            "country": "US",
            "registration_date": "2024-06-01",
            "raw_data": {},
        }
        mock_backend_class.from_rir_config.return_value = mock_backend

        runner = make_runner(SyncPrefixesJob)
        runner.run(
            aggregate_id=agg.pk,
            parent_handle=parent_net.handle,
            user_key_id=rir_user_key.pk,
        )

        mock_backend.get_customer.assert_called_once_with("C09999999")
        assert RIRCustomer.objects.filter(handle="C09999999").exists()
        customer = RIRCustomer.objects.get(handle="C09999999")
        assert customer.customer_name == "Child Customer"
        assert customer.network == RIRNetwork.objects.get(handle="NET-CHILD-1")

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
    def reassign_setup(self, rir_user_key, rir_organization, prefix_under_parent):
        """An opted-in parent with a child prefix whose tenant is linked to an RIROrganization.

        The linked org makes the job take the detailed reassignment path.
        """
        setup = prefix_under_parent("10.0.0.0/20", "10.0.1.0/29", "NET-PARENT-20", auto_reassign=True)
        rir_organization.tenant = setup["tenant"]
        rir_organization.save()
        return setup

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_preflight_syncs_existing_reassignment(self, mock_backend_class, reassign_setup, rir_config, rir_user_key):
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
        log = RIRSyncLog.objects.filter(object_handle="NET-INTERMEDIATE-24", status="skipped").first()
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
        _parent_handle, net_data = mock_backend.reassign_network.call_args[0]
        assert net_data["net_name"] == "TEST-TENANT-10-0-1-0-29"

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_refuses_parent_not_opted_in(self, mock_backend_class, reassign_setup, rir_user_key):
        """The job is the automatic path, so it only runs under the parent's auto_reassign opt-in."""
        from netbox_rir_manager.jobs import ReassignJob

        reassign_setup["parent"].auto_reassign = False
        reassign_setup["parent"].save()

        runner = make_runner(ReassignJob)
        runner.run(prefix_id=reassign_setup["prefix"].pk, user_key_id=rir_user_key.pk)

        assert runner.job.data["status"] == "error"
        mock_backend_class.from_rir_config.assert_not_called()

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_simple_reassignment_without_site_reports_error(
        self, mock_backend_class, reassign_setup, rir_organization, rir_user_key
    ):
        """A prefix with no site scope stops cleanly instead of treating Prefix.site as a Site."""
        from netbox_rir_manager.jobs import ReassignJob

        rir_organization.tenant = None  # no linked org, so the simple path runs
        rir_organization.save()
        mock_backend = MagicMock()
        mock_backend.find_net.return_value = None
        mock_backend_class.from_rir_config.return_value = mock_backend

        runner = make_runner(ReassignJob)
        runner.run(prefix_id=reassign_setup["prefix"].pk, user_key_id=rir_user_key.pk)

        assert runner.job.data == {
            "prefix": "10.0.1.0/29",
            "status": "error",
            "message": "Prefix has no site",
            "reassignment_type": "simple",
        }
        mock_backend.reassign_network.assert_not_called()


@pytest.mark.django_db
class TestRemoveNetworkJob:
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_remove_success(self, mock_backend_class, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import RemoveNetworkJob
        from netbox_rir_manager.models import RIRNetwork, RIRSyncLog

        net = RIRNetwork.objects.create(rir_config=rir_config, handle="NET-REMOVE-1", net_name="REMOVE-NET")

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
        """ARIN's reason for refusing the removal is the job's message."""
        from netbox_rir_manager.backends.base import RIRRequestError
        from netbox_rir_manager.jobs import RemoveNetworkJob
        from netbox_rir_manager.models import RIRNetwork, RIRSyncLog

        net = RIRNetwork.objects.create(rir_config=rir_config, handle="NET-RMFAIL-1", net_name="FAIL-NET")

        mock_backend = MagicMock()
        mock_backend.remove_network.side_effect = RIRRequestError(NOT_FOUND)
        mock_backend_class.from_rir_config.return_value = mock_backend

        runner = make_runner(RemoveNetworkJob)

        runner.run(network_id=net.pk, user_key_id=rir_user_key.pk)

        assert runner.job.data["status"] == "error"
        assert runner.job.data["message"] == f"Failed to remove network from ARIN: {NOT_FOUND}"

        log = RIRSyncLog.objects.get(object_handle="NET-RMFAIL-1", operation="remove")
        assert log.status == "error"


def _prefix_sync_kwargs(rir_config, rir):
    from ipam.models import Aggregate

    agg = Aggregate.objects.create(prefix="10.70.0.0/16", rir=rir)
    return {"aggregate_id": agg.pk, "parent_handle": "NET-KEYCHECK-AGG"}


def _reassign_kwargs(rir_config, rir):
    from ipam.models import Prefix

    return {"prefix_id": Prefix.objects.create(prefix="10.71.1.0/24").pk}


def _remove_kwargs(rir_config, rir):
    from netbox_rir_manager.models import RIRNetwork

    network = RIRNetwork.objects.create(rir_config=rir_config, handle="NET-KEYCHECK-RM")
    return {"network_id": network.pk}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "job_name, make_kwargs",
    [
        pytest.param("SyncPrefixesJob", _prefix_sync_kwargs, id="prefix-sync"),
        pytest.param("ReassignJob", _reassign_kwargs, id="reassign"),
        pytest.param("RemoveNetworkJob", _remove_kwargs, id="remove"),
    ],
)
@patch("netbox_rir_manager.jobs.ARINBackend")
def test_queued_job_refuses_key_of_deactivated_owner(
    mock_backend_class, rir_config, rir, rir_user_key, job_name, make_kwargs
):
    """A job queued before its key's owner was deactivated never calls ARIN with that key."""
    from netbox_rir_manager import jobs
    from netbox_rir_manager.models import RIRSyncLog

    kwargs = make_kwargs(rir_config, rir)
    rir_user_key.user.is_active = False
    rir_user_key.user.save()

    runner = make_runner(getattr(jobs, job_name))
    runner.run(user_key_id=rir_user_key.pk, **kwargs)

    mock_backend_class.from_rir_config.assert_not_called()
    assert runner.job.data["status"] == "skipped"
    assert f"{rir_user_key.user.username} is deactivated" in runner.job.data["message"]
    log = RIRSyncLog.objects.get(rir_config=rir_config, status="skipped")
    assert log.message == runner.job.data["message"]


@pytest.mark.django_db
class TestChangelogEntries:
    """Verify that sync operations create ObjectChange changelog entries."""

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_creates_changelog_for_org(self, mock_backend_class, rir_config, admin_user, rir_user_key):
        """SyncRIRConfigJob creates ObjectChange entries when a real user is present."""
        from core.models import ObjectChange

        from netbox_rir_manager.jobs import SyncRIRConfigJob
        from netbox_rir_manager.models import RIROrganization

        wire_org(mock_backend_class, "CHANGELOG-ARIN", "Changelog Org")

        runner = make_runner(SyncRIRConfigJob)
        runner.job.object_id = rir_config.pk
        runner.job.user = admin_user

        runner.run()

        assert RIROrganization.objects.filter(handle="CHANGELOG-ARIN").exists()
        org = RIROrganization.objects.get(handle="CHANGELOG-ARIN")
        changes = ObjectChange.objects.filter(
            changed_object_id=org.pk,
            changed_object_type__model="rirorganization",
        )
        assert changes.exists()
        assert changes.first().user == admin_user

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_sync_no_changelog_without_user(self, mock_backend_class, rir_config, default_key):
        """A sync with no user runs with the default key and creates no ObjectChange."""
        from core.models import ObjectChange

        from netbox_rir_manager.jobs import SyncRIRConfigJob

        wire_org(mock_backend_class, "NOLOG-ARIN", "No Log Org")

        runner = make_runner(SyncRIRConfigJob)
        runner.job.object_id = rir_config.pk
        runner.job.user = None

        initial_count = ObjectChange.objects.count()
        runner.run()

        # No ObjectChange should be created since user is not a real User
        assert ObjectChange.objects.count() == initial_count

    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_scheduled_sync_attributes_changes_to_default_key_owner(self, mock_backend_class, rir_config, default_key):
        """The scheduled sync logs its changes under the owner of the key that made the calls."""
        from core.models import ObjectChange

        from netbox_rir_manager.jobs import ScheduledRIRSyncJob
        from netbox_rir_manager.models import RIROrganization

        wire_org(mock_backend_class, "SCHEDLOG-ARIN", "Scheduled Log Org")

        runner = make_runner(ScheduledRIRSyncJob)
        runner.job.user = None
        runner.run()

        org = RIROrganization.objects.get(handle="SCHEDLOG-ARIN")
        change = ObjectChange.objects.get(changed_object_id=org.pk, changed_object_type__model="rirorganization")
        assert change.user == default_key.user


@pytest.mark.django_db
class TestReassignJobOutcome:
    """The job reports a reassignment ARIN accepted as a success, ticket or not."""

    @pytest.mark.parametrize(
        "reassign_result, expected_message, expected_ticket",
        [
            pytest.param(immediate_result("NET-10-0-1-0-1"), "immediately", None, id="no-ticket"),
            pytest.param(ticket_result("TKT-JOB-1"), "ticket TKT-JOB-1", "TKT-JOB-1", id="ticket"),
            pytest.param(ticket_result(EXISTING_TICKET), "could not record", None, id="recording-fails"),
        ],
    )
    @patch("netbox_rir_manager.jobs.ARINBackend")
    def test_reports_success(
        self,
        mock_backend_class,
        rir_user_key,
        rir_organization,
        rir_ticket,
        prefix_under_parent,
        reassign_result,
        expected_message,
        expected_ticket,
    ):
        from netbox_rir_manager.jobs import ReassignJob

        setup = prefix_under_parent("10.0.0.0/20", "10.0.1.0/29", "NET-PARENT-20", auto_reassign=True)
        rir_organization.tenant = setup["tenant"]
        rir_organization.save()
        backend = mock_backend_class.from_rir_config.return_value
        backend.find_net.return_value = None
        backend.reassign_network.return_value = reassign_result

        runner = make_runner(ReassignJob)
        runner.run(prefix_id=setup["prefix"].pk, user_key_id=rir_user_key.pk)

        assert runner.job.data["status"] == "success"
        assert expected_message in runner.job.data["message"]
        assert runner.job.data.get("ticket_number") == expected_ticket


def test_plugin_ready_registers_scheduled_sync(reload_plugin_module):
    """Loading the plugin registers the scheduled sync, not only once something imports jobs.py.

    rqworker schedules system jobs from the registry at startup, before any view or signal
    handler has imported the jobs module lazily.
    """
    from django.apps import apps
    from netbox.registry import registry

    reload_plugin_module("jobs", load=False)

    with patch.dict(registry["system_jobs"], clear=True), patch("netbox.plugins.PluginConfig.ready"):
        apps.get_app_config("netbox_rir_manager").ready()
        registered = [cls.__name__ for cls in registry["system_jobs"]]

    assert registered == ["ScheduledRIRSyncJob"]


def test_scheduled_sync_interval_defaults_to_daily():
    from netbox_rir_manager.jobs import scheduled_sync_interval

    assert scheduled_sync_interval() == 1440


@pytest.mark.parametrize("hours", [0, "24", True])
def test_scheduled_sync_interval_rejects_invalid_values(plugin_settings, hours):
    from django.core.exceptions import ImproperlyConfigured

    from netbox_rir_manager.jobs import scheduled_sync_interval

    plugin_settings(sync_interval_hours=hours)

    with pytest.raises(ImproperlyConfigured, match="sync_interval_hours"):
        scheduled_sync_interval()


def test_scheduled_sync_registered_with_configured_interval(plugin_settings, reload_plugin_module):
    """The system job is registered with sync_interval_hours, converted to minutes."""
    from netbox.registry import registry

    plugin_settings(sync_interval_hours=6)

    with patch.dict(registry["system_jobs"], clear=True):
        reload_plugin_module("jobs")
        intervals = {cls.__name__: kwargs["interval"] for cls, kwargs in registry["system_jobs"].items()}

    assert intervals == {"ScheduledRIRSyncJob": 360}
