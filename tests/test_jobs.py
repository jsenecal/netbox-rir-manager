from unittest.mock import MagicMock, patch

import pytest

from tests.arin_payloads import EXISTING_TICKET, NOT_FOUND, arin_net, arin_org, immediate_result, ticket_result


def make_runner(cls):
    """Create a job runner with mocked job and logger (bypasses __init__)."""
    runner = cls.__new__(cls)
    runner.job = MagicMock()
    runner.job.data = {}
    runner.logger = MagicMock()
    return runner


@pytest.mark.django_db
class TestScheduledSyncJob:
    def test_scheduled_sync_all_active_configs(self, mock_arin, rir_config, default_key):
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob
        from netbox_rir_manager.models import RIROrganization

        mock_arin("jobs", get_organization=arin_org("SCHED-ARIN", "Scheduled Org"))

        make_runner(ScheduledRIRSyncJob).run()

        assert RIROrganization.objects.filter(handle="SCHED-ARIN").exists()

    def test_scheduled_sync_skips_inactive_configs(self, mock_arin, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        arin = mock_arin("jobs")
        rir_config.is_active = False
        rir_config.save()

        make_runner(ScheduledRIRSyncJob).run()

        arin.for_user_key.assert_not_called()

    def test_scheduled_sync_uses_only_default_key(self, mock_arin, rir_config, default_key, operator_key):
        """Scheduled sync has no acting user: it syncs once with the default key, never other users' keys."""
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        arin = mock_arin("jobs")

        make_runner(ScheduledRIRSyncJob).run()

        arin.for_user_key.assert_called_once_with(default_key)

    @patch("netbox_rir_manager.jobs.SyncPrefixesJob")
    def test_scheduled_sync_queues_prefix_discovery_with_default_key(
        self, mock_prefix_job, mock_arin, rir_config, default_key, operator_key, rir
    ):
        """Like the manual sync, each owned aggregate gets one prefix sync, run with the default key as its owner."""
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        agg = Aggregate.objects.create(prefix="10.0.0.0/8", rir=rir)
        mock_arin("jobs", find_net=arin_net("NET-10-0-0-0-1", org_handle=rir_config.org_handle))

        make_runner(ScheduledRIRSyncJob).run()

        mock_prefix_job.enqueue.assert_called_once_with(
            instance=rir_config,
            user=default_key.user,
            aggregate_id=agg.pk,
            parent_handle="NET-10-0-0-0-1",
            user_key_id=default_key.pk,
        )

    def test_scheduled_sync_skips_config_without_default_key(self, mock_arin, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        arin = mock_arin("jobs")

        make_runner(ScheduledRIRSyncJob).run()

        arin.for_user_key.assert_not_called()

    def test_scheduled_sync_skips_config_whose_default_key_owner_is_deactivated(
        self, mock_arin, rir_config, default_key
    ):
        from netbox_rir_manager.jobs import ScheduledRIRSyncJob

        arin = mock_arin("jobs")
        default_key.user.is_active = False
        default_key.user.save()

        runner = make_runner(ScheduledRIRSyncJob)
        runner.run()

        arin.for_user_key.assert_not_called()
        warning = runner.logger.warning.call_args[0][0]
        assert "deactivated user" in warning


@pytest.mark.django_db
class TestRIRSyncJob:
    def test_sync_creates_org_and_log(self, mock_arin, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIROrganization, RIRSyncLog

        org = arin_org(
            "TESTORG-ARIN", "Test Org", city="Anytown", state_province="VA", postal_code="12345", country="US"
        )
        mock_arin("jobs", get_organization=org)

        logs, agg_nets = sync_rir_config(rir_user_key, resource_types=["organizations"])

        assert len(logs) == 1
        assert logs[0].status == "success"
        assert agg_nets == []
        assert RIROrganization.objects.filter(handle="TESTORG-ARIN").exists()
        assert RIRSyncLog.objects.filter(rir_config=rir_config).count() == 1

    def test_sync_error_creates_error_log(self, mock_arin, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRSyncLog

        mock_arin("jobs", get_organization=None)

        logs, agg_nets = sync_rir_config(rir_user_key, resource_types=["organizations"])

        assert len(logs) == 1
        assert logs[0].status == "error"
        assert agg_nets == []
        assert RIRSyncLog.objects.filter(rir_config=rir_config, status="error").count() == 1

    def test_sync_updates_last_sync(self, mock_arin, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import sync_rir_config

        mock_arin("jobs")

        assert rir_config.last_sync is None
        sync_rir_config(rir_user_key, resource_types=["organizations"])

        rir_config.refresh_from_db()
        assert rir_config.last_sync is not None

    def test_sync_contacts_from_org(self, mock_arin, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRContact, RIROrganization

        mock_arin(
            "jobs",
            get_organization=arin_org(
                "TESTORG-ARIN", "Test Org", poc_links=[{"handle": "JD123-ARIN", "function": "AD"}], city="Anytown"
            ),
            get_poc={
                "handle": "JD123-ARIN",
                "contact_type": "PERSON",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Test Org",
                "email": "john@example.com",
                "phone": "",
                "raw_data": {},
            },
        )

        sync_rir_config(rir_user_key, resource_types=["organizations", "contacts"])

        assert RIROrganization.objects.filter(handle="TESTORG-ARIN").exists()
        contact = RIRContact.objects.get(handle="JD123-ARIN")
        assert contact.first_name == "John"
        assert contact.last_name == "Doe"

    def test_sync_contacts_poc_in_several_roles_synced_once(self, mock_arin, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIROrganization, RIRSyncLog

        poc_links = [
            {"handle": "NOC11106-ARIN", "function": "N"},
            {"handle": "NOC11106-ARIN", "function": "T"},
            {"handle": "JD123-ARIN", "function": "AD"},
        ]
        backend = mock_arin("jobs", get_organization=arin_org("TESTORG-ARIN", "Test Org", poc_links=poc_links)).backend
        backend.get_poc.side_effect = lambda handle: {
            "handle": handle,
            "contact_type": "ROLE",
            "last_name": handle,
            "raw_data": {},
        }

        sync_rir_config(rir_user_key, resource_types=["organizations", "contacts"])

        fetched = [c.args[0] for c in backend.get_poc.call_args_list]
        assert fetched == ["NOC11106-ARIN", "JD123-ARIN"]
        assert (
            RIRSyncLog.objects.filter(object_type="contact", object_handle="NOC11106-ARIN", status="success").count()
            == 1
        )
        assert RIROrganization.objects.get(handle="TESTORG-ARIN").raw_data["poc_links"] == poc_links

    def test_sync_networks_from_ipam(self, mock_arin, rir_config, rir_user_key, aggregate):
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRNetwork

        block = {"start_address": "192.0.2.0", "end_address": "192.0.2.255", "cidr_length": 24, "type": "DS"}
        mock_arin(
            "jobs",
            find_net=arin_net("NET-192-0-2-0-1", net_name="EXAMPLE-NET", org_handle="TESTORG-ARIN", net_blocks=[block]),
        )

        logs, agg_nets = sync_rir_config(rir_user_key, resource_types=["networks"])

        net = RIRNetwork.objects.get(handle="NET-192-0-2-0-1")
        assert net.net_name == "EXAMPLE-NET"
        assert net.aggregate == aggregate
        assert len(agg_nets) == 1

    def test_sync_sets_synced_by(self, mock_arin, rir_config, rir_user_key):
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIROrganization

        mock_arin("jobs", get_organization=arin_org("SYNCBY-ARIN", "Sync By Org"))

        sync_rir_config(rir_user_key)

        org = RIROrganization.objects.get(handle="SYNCBY-ARIN")
        assert org.synced_by == rir_user_key

    def test_sync_job_runner(self, mock_arin, rir_config, admin_user):
        from netbox_rir_manager.jobs import SyncRIRConfigJob
        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(user=admin_user, rir_config=rir_config, api_key="job-key")
        arin = mock_arin("jobs")

        runner = make_runner(SyncRIRConfigJob)
        runner.job.object_id = rir_config.pk
        runner.job.user = admin_user

        runner.run()

        assert "rir_config" in runner.job.data
        arin.for_user_key.assert_called_once_with(key)

    @patch("netbox_rir_manager.jobs.SyncPrefixesJob")
    def test_sync_job_queues_prefix_discovery_with_users_key(
        self, mock_prefix_job, mock_arin, rir_config, default_key, operator_key, rir
    ):
        """A manual sync queues one prefix sync per owned aggregate, with the requesting user's own key."""
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import SyncRIRConfigJob

        agg = Aggregate.objects.create(prefix="10.0.0.0/8", rir=rir)
        mock_arin("jobs", find_net=arin_net("NET-10-0-0-0-1", org_handle=rir_config.org_handle))

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

    def test_sync_job_without_users_key_does_nothing(self, mock_arin, rir_config, default_key, make_user):
        """A user-triggered sync never borrows the default key."""
        from netbox_rir_manager.jobs import SyncRIRConfigJob

        arin = mock_arin("jobs")
        runner = make_runner(SyncRIRConfigJob)
        runner.job.object_id = rir_config.pk
        runner.job.user = make_user("keyless")

        runner.run()

        arin.for_user_key.assert_not_called()
        assert runner.job.data["status"] == "error"

    def test_sync_returns_agg_nets(self, mock_arin, rir_config, rir_user_key, rir):
        """sync_rir_config returns (logs, agg_nets) with aggregate/network pairs."""
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="10.0.0.0/8", rir=rir)
        mock_arin("jobs", find_net=arin_net("NET-10-0-0-0-1", org_handle=rir_config.org_handle))

        logs, agg_nets = sync_rir_config(rir_user_key, resource_types=["networks"])

        assert len(logs) == 1
        assert len(agg_nets) == 1
        returned_agg, returned_net = agg_nets[0]
        assert returned_agg.pk == agg.pk
        assert isinstance(returned_net, RIRNetwork)
        assert returned_net.handle == "NET-10-0-0-0-1"

    def test_sync_walks_up_to_net_owned_by_config_org(self, mock_arin, rir_config, rir_user_key, aggregate):
        """When the most specific net is a child, the aggregate links to our parent net instead."""
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRNetwork

        backend = mock_arin(
            "jobs",
            find_net=arin_net("NET-CHILD-1", org_handle="OTHER-ARIN", parent_handle="NET-PARENT-1"),
            get_network=arin_net("NET-PARENT-1", org_handle="TESTORG-ARIN", parent_handle="NET-UPSTREAM-1"),
        ).backend

        logs, agg_nets = sync_rir_config(rir_user_key, resource_types=["networks"])

        backend.get_network.assert_called_once_with("NET-PARENT-1")
        assert RIRNetwork.objects.get(handle="NET-PARENT-1").aggregate == aggregate
        assert not RIRNetwork.objects.filter(handle="NET-CHILD-1").exists()
        assert [net.handle for _agg, net in agg_nets] == ["NET-PARENT-1"]

    @pytest.mark.parametrize(
        "config_org, found, parent, expected_lookups, owner_in_message",
        [
            pytest.param(
                "TESTORG-ARIN",
                arin_net("NET-CUST-1", customer_handle="C01234567", parent_handle="NET-THEIRS-1"),
                arin_net("NET-THEIRS-1", org_handle="OTHER-ARIN"),
                1,
                "C01234567",
                id="chain-owned-by-another-org",
            ),
            pytest.param(
                "TESTORG-ARIN",
                arin_net("NET-A", org_handle="OTHER-ARIN", parent_handle="NET-B"),
                arin_net("NET-B", org_handle="OTHER-ARIN", parent_handle="NET-A"),
                1,
                "OTHER-ARIN",
                id="parent-chain-cycle",
            ),
            pytest.param(
                "TESTORG-ARIN",
                arin_net("NET-A", org_handle="OTHER-ARIN", parent_handle="NET-B"),
                None,
                1,
                "OTHER-ARIN",
                id="parent-net-unavailable",
            ),
            pytest.param(
                "",
                arin_net("NET-A", org_handle="OTHER-ARIN", parent_handle="NET-B"),
                None,
                0,
                "OTHER-ARIN",
                id="config-without-org-handle",
            ),
            pytest.param("TESTORG-ARIN", None, None, 0, "", id="no-net-at-arin"),
        ],
    )
    def test_sync_skips_aggregate_not_owned_by_config_org(
        self,
        mock_arin,
        rir_config,
        rir_user_key,
        aggregate,
        config_org,
        found,
        parent,
        expected_lookups,
        owner_in_message,
    ):
        """An aggregate whose net chain never reaches the config org is skipped and logged, not synced."""
        from netbox_rir_manager.jobs import sync_rir_config
        from netbox_rir_manager.models import RIRNetwork

        rir_config.org_handle = config_org
        rir_config.save()
        backend = mock_arin("jobs", find_net=found, get_network=parent).backend

        logs, agg_nets = sync_rir_config(rir_user_key, resource_types=["networks"])

        assert agg_nets == []
        assert not RIRNetwork.objects.exists()
        backend.get_customer.assert_not_called()
        assert [log.status for log in logs] == ["skipped"]
        assert owner_in_message in logs[0].message
        assert backend.get_network.call_count == expected_lookups

    @pytest.mark.parametrize(
        "prefix, expected_range",
        [
            pytest.param("192.0.2.8/31", ("192.0.2.8", "192.0.2.9"), id="ipv4-31"),
            pytest.param("192.0.2.8/32", ("192.0.2.8", "192.0.2.8"), id="ipv4-32"),
        ],
    )
    def test_sync_queries_last_address_of_host_aggregate(
        self, mock_arin, rir_config, rir_user_key, rir, prefix, expected_range
    ):
        """A /31 or /32 aggregate is looked up by its real last address, not "None"."""
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import sync_rir_config

        agg = Aggregate.objects.create(prefix=prefix, rir=rir)
        backend = mock_arin("jobs", find_net=arin_net("NET-HOST-1", org_handle="TESTORG-ARIN")).backend

        _logs, agg_nets = sync_rir_config(rir_user_key, resource_types=["networks"])

        backend.find_net.assert_called_once_with(*expected_range)
        assert [(a.pk, net.handle) for a, net in agg_nets] == [(agg.pk, "NET-HOST-1")]


@pytest.mark.django_db
class TestSyncPrefixesJob:
    @pytest.fixture
    def run_prefix_sync(self, rir_user_key):
        """Run SyncPrefixesJob over a prefix_under_parent setup with the admin user's key."""
        from netbox_rir_manager.jobs import SyncPrefixesJob

        def _run(setup):
            runner = make_runner(SyncPrefixesJob)
            runner.run(aggregate_id=setup["agg"].pk, parent_handle=setup["parent"].handle, user_key_id=rir_user_key.pk)
            return runner

        return _run

    @pytest.mark.parametrize(
        "prefix, expected_range",
        [
            pytest.param("10.0.1.8/31", ("10.0.1.8", "10.0.1.9"), id="ipv4-31"),
            pytest.param("10.0.1.8/32", ("10.0.1.8", "10.0.1.8"), id="ipv4-32"),
        ],
    )
    def test_discovers_host_prefix_reassignment(
        self, mock_arin, prefix_under_parent, run_prefix_sync, prefix, expected_range
    ):
        """/31 and /32 child prefixes are looked up by their real last address and synced."""
        from netbox_rir_manager.models import RIRNetwork

        setup = prefix_under_parent("10.0.0.0/20", prefix, "NET-PARENT-20")
        backend = mock_arin("jobs", find_net=arin_net("NET-HOST-1", parent_handle="NET-PARENT-20")).backend

        run_prefix_sync(setup)

        backend.find_net.assert_called_once_with(*expected_range)
        assert RIRNetwork.objects.get(handle="NET-HOST-1").prefix == setup["prefix"]

    def test_discovers_child_prefixes(self, mock_arin, prefix_under_parent, run_prefix_sync):
        """SyncPrefixesJob discovers and syncs child prefix networks."""
        from ipam.models import Prefix

        from netbox_rir_manager.models import RIRNetwork, RIRSyncLog

        setup = prefix_under_parent("10.0.0.0/20", "10.0.1.0/24", "NET-PARENT-20")
        Prefix.objects.create(prefix="10.0.2.0/24")
        nets = {
            "10.0.1.0": arin_net("NET-CHILD-1", parent_handle="NET-PARENT-20"),
            # The parent itself: no reassignment for this prefix, so nothing to sync.
            "10.0.2.0": arin_net("NET-PARENT-20"),
        }
        mock_arin("jobs").backend.find_net.side_effect = lambda start, end: nets.get(start)

        run_prefix_sync(setup)

        assert RIRNetwork.objects.filter(handle="NET-CHILD-1").exists()
        assert RIRNetwork.objects.filter(handle="NET-PARENT-20").count() == 1
        assert RIRSyncLog.objects.filter(object_handle="NET-CHILD-1").exists()

    def test_discovers_customer_for_child_prefix(self, mock_arin, prefix_under_parent, run_prefix_sync):
        """SyncPrefixesJob fetches and persists customers for child networks with customer_handle."""
        from netbox_rir_manager.models import RIRCustomer, RIRNetwork

        setup = prefix_under_parent("10.0.0.0/20", "10.0.1.0/24", "NET-PARENT-20")
        backend = mock_arin(
            "jobs",
            find_net=arin_net(
                "NET-CHILD-1", org_handle=None, parent_handle="NET-PARENT-20", customer_handle="C09999999"
            ),
            get_customer={
                "handle": "C09999999",
                "customer_name": "Child Customer",
                "street_address": "",
                "city": "Springfield",
                "state_province": "IL",
                "postal_code": "62701",
                "country": "US",
                "registration_date": "2024-06-01",
                "raw_data": {},
            },
        ).backend

        run_prefix_sync(setup)

        backend.get_customer.assert_called_once_with("C09999999")
        customer = RIRCustomer.objects.get(handle="C09999999")
        assert customer.customer_name == "Child Customer"
        assert customer.network == RIRNetwork.objects.get(handle="NET-CHILD-1")

    def test_logs_progress(self, mock_arin, prefix_under_parent, run_prefix_sync):
        """SyncPrefixesJob logs progress via self.logger."""
        setup = prefix_under_parent("10.0.0.0/20", "10.0.1.0/24", "NET-PARENT-20")
        mock_arin("jobs")

        runner = run_prefix_sync(setup)

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

    @pytest.fixture
    def run_reassign(self, reassign_setup, rir_user_key):
        """Run ReassignJob for the reassign_setup prefix with the admin user's key."""
        from netbox_rir_manager.jobs import ReassignJob

        def _run():
            runner = make_runner(ReassignJob)
            runner.run(prefix_id=reassign_setup["prefix"].pk, user_key_id=rir_user_key.pk)
            return runner

        return _run

    def test_preflight_syncs_existing_reassignment(self, mock_arin, reassign_setup, run_reassign):
        """When ARIN returns a different net than parent, job syncs and returns early."""
        from netbox_rir_manager.models import RIRNetwork, RIRSyncLog

        backend = mock_arin("jobs", find_net=arin_net("NET-INTERMEDIATE-24", net_type="RS")).backend

        runner = run_reassign()

        assert runner.job.data["status"] == "synced"
        assert "NET-INTERMEDIATE-24" in runner.job.data["message"]
        backend.reassign_network.assert_not_called()
        assert RIRNetwork.objects.get(handle="NET-INTERMEDIATE-24").prefix == reassign_setup["prefix"]
        log = RIRSyncLog.objects.get(object_handle="NET-INTERMEDIATE-24", status="skipped")
        assert "already reassigned" in log.message

    def test_preflight_proceeds_when_arin_returns_parent(self, mock_arin, run_reassign):
        """When ARIN returns the parent handle, pre-flight passes and reassignment proceeds."""
        # The reassignment itself fails; the test only needs it to have been attempted.
        backend = mock_arin("jobs", find_net=arin_net("NET-PARENT-20"), reassign_network=None).backend

        run_reassign()

        backend.reassign_network.assert_called_once()

    def test_preflight_proceeds_when_arin_returns_none(self, mock_arin, run_reassign):
        """When ARIN returns None for find_net, pre-flight passes and reassignment proceeds."""
        backend = mock_arin("jobs", reassign_network=None).backend

        run_reassign()

        backend.reassign_network.assert_called_once()
        _parent_handle, net_data = backend.reassign_network.call_args[0]
        assert net_data["net_name"] == "TEST-TENANT-10-0-1-0-29"

    def test_refuses_parent_not_opted_in(self, mock_arin, reassign_setup, run_reassign):
        """The job is the automatic path, so it only runs under the parent's auto_reassign opt-in."""
        arin = mock_arin("jobs")
        reassign_setup["parent"].auto_reassign = False
        reassign_setup["parent"].save()

        runner = run_reassign()

        assert runner.job.data["status"] == "error"
        arin.for_user_key.assert_not_called()

    def test_simple_reassignment_without_site_reports_error(self, mock_arin, rir_organization, run_reassign):
        """A prefix with no site scope stops cleanly instead of treating Prefix.site as a Site."""
        rir_organization.tenant = None  # no linked org, so the simple path runs
        rir_organization.save()
        backend = mock_arin("jobs").backend

        runner = run_reassign()

        assert runner.job.data == {
            "prefix": "10.0.1.0/29",
            "status": "error",
            "message": "Prefix has no site",
            "reassignment_type": "simple",
        }
        backend.reassign_network.assert_not_called()

    @pytest.mark.parametrize(
        "reassign_result, expected_message, expected_ticket",
        [
            pytest.param(immediate_result("NET-10-0-1-0-1"), "immediately", None, id="no-ticket"),
            pytest.param(ticket_result("TKT-JOB-1"), "ticket TKT-JOB-1", "TKT-JOB-1", id="ticket"),
            pytest.param(ticket_result(EXISTING_TICKET), "could not record", None, id="recording-fails"),
        ],
    )
    def test_reports_success(
        self, mock_arin, rir_ticket, run_reassign, reassign_result, expected_message, expected_ticket
    ):
        """The job reports a reassignment ARIN accepted as a success, ticket or not."""
        mock_arin("jobs", reassign_network=reassign_result)

        runner = run_reassign()

        assert runner.job.data["status"] == "success"
        assert expected_message in runner.job.data["message"]
        assert runner.job.data.get("ticket_number") == expected_ticket

    @patch("netbox_rir_manager.services.geocoding.NominatimGeocoder._get_geocoder")
    def test_unmappable_subdivision_fails_cleanly(
        self, mock_get_geocoder, mock_arin, reassign_setup, rir_organization, rir_user_key
    ):
        """Issue #83: an unmappable state name stops the job with a clear error, not a DataError."""
        from types import SimpleNamespace

        from dcim.models import Site

        from netbox_rir_manager.jobs import ReassignJob
        from netbox_rir_manager.models import RIRAddress, RIRSyncLog

        rir_organization.tenant = None  # no linked org, so the simple path runs
        rir_organization.save()
        site = Site.objects.create(name="Site NRW", slug="site-nrw", physical_address="1 Main Street, Town")
        prefix = reassign_setup["prefix"]
        prefix.scope = site
        prefix.save()
        mock_get_geocoder.return_value.geocode.return_value = SimpleNamespace(
            raw={"address": {"country_code": "de", "city": "Town", "state": "North Rhine-Westphalia"}}
        )
        mock_backend = mock_arin("jobs").backend

        runner = make_runner(ReassignJob)
        runner.run(prefix_id=prefix.pk, user_key_id=rir_user_key.pk)

        message = (
            "Could not determine the ISO 3166-2 subdivision code for 'North Rhine-Westphalia'; "
            "enter it on the Site's RIR address."
        )
        assert (runner.job.data["status"], runner.job.data["message"]) == ("error", message)
        log = RIRSyncLog.objects.get(status="error")
        assert (log.operation, log.object_type, log.object_handle, log.message) == (
            "reassign",
            "customer",
            "NET-PARENT-20",
            f"{prefix.prefix}: {message}",
        )
        assert not RIRAddress.objects.filter(site=site).exists()
        mock_backend.create_customer.assert_not_called()
        mock_backend.reassign_network.assert_not_called()


@pytest.mark.django_db
class TestRemoveNetworkJob:
    def test_remove_success(self, mock_arin, make_network, rir_user_key):
        from netbox_rir_manager.jobs import RemoveNetworkJob
        from netbox_rir_manager.models import RIRSyncLog

        net = make_network("NET-REMOVE-1", net_name="REMOVE-NET")
        backend = mock_arin("jobs", remove_network=True).backend

        runner = make_runner(RemoveNetworkJob)
        runner.run(network_id=net.pk, user_key_id=rir_user_key.pk)

        backend.remove_network.assert_called_once_with("NET-REMOVE-1")
        assert runner.job.data["status"] == "success"
        log = RIRSyncLog.objects.get(object_handle="NET-REMOVE-1", operation="remove")
        assert log.status == "success"
        assert "Removed" in log.message

    def test_remove_failure(self, mock_arin, make_network, rir_user_key):
        """ARIN's reason for refusing the removal is the job's message."""
        from netbox_rir_manager.backends.base import RIRRequestError
        from netbox_rir_manager.jobs import RemoveNetworkJob
        from netbox_rir_manager.models import RIRSyncLog

        net = make_network("NET-RMFAIL-1", net_name="FAIL-NET")
        mock_arin("jobs").backend.remove_network.side_effect = RIRRequestError(NOT_FOUND)

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
def test_queued_job_refuses_key_of_deactivated_owner(mock_arin, rir_config, rir, rir_user_key, job_name, make_kwargs):
    """A job queued before its key's owner was deactivated never calls ARIN with that key."""
    from netbox_rir_manager import jobs
    from netbox_rir_manager.models import RIRSyncLog

    arin = mock_arin("jobs")
    kwargs = make_kwargs(rir_config, rir)
    rir_user_key.user.is_active = False
    rir_user_key.user.save()

    runner = make_runner(getattr(jobs, job_name))
    runner.run(user_key_id=rir_user_key.pk, **kwargs)

    arin.for_user_key.assert_not_called()
    assert runner.job.data["status"] == "skipped"
    assert f"{rir_user_key.user.username} is deactivated" in runner.job.data["message"]
    log = RIRSyncLog.objects.get(rir_config=rir_config, status="skipped")
    assert log.message == runner.job.data["message"]


@pytest.mark.django_db
class TestChangelogEntries:
    """Verify that sync operations create ObjectChange changelog entries."""

    def test_sync_creates_changelog_for_org(self, mock_arin, rir_config, admin_user, rir_user_key):
        """SyncRIRConfigJob creates ObjectChange entries when a real user is present."""
        from core.models import ObjectChange

        from netbox_rir_manager.jobs import SyncRIRConfigJob
        from netbox_rir_manager.models import RIROrganization

        mock_arin("jobs", get_organization=arin_org("CHANGELOG-ARIN", "Changelog Org"))

        runner = make_runner(SyncRIRConfigJob)
        runner.job.object_id = rir_config.pk
        runner.job.user = admin_user
        runner.run()

        org = RIROrganization.objects.get(handle="CHANGELOG-ARIN")
        changes = ObjectChange.objects.filter(
            changed_object_id=org.pk,
            changed_object_type__model="rirorganization",
        )
        assert changes.exists()
        assert changes.first().user == admin_user

    def test_sync_no_changelog_without_user(self, mock_arin, rir_config, default_key):
        """A sync with no user runs with the default key and creates no ObjectChange."""
        from core.models import ObjectChange

        from netbox_rir_manager.jobs import SyncRIRConfigJob

        mock_arin("jobs", get_organization=arin_org("NOLOG-ARIN", "No Log Org"))

        runner = make_runner(SyncRIRConfigJob)
        runner.job.object_id = rir_config.pk
        runner.job.user = None

        initial_count = ObjectChange.objects.count()
        runner.run()

        assert ObjectChange.objects.count() == initial_count

    def test_scheduled_sync_attributes_changes_to_default_key_owner(self, mock_arin, rir_config, default_key):
        """The scheduled sync logs its changes under the owner of the key that made the calls."""
        from core.models import ObjectChange

        from netbox_rir_manager.jobs import ScheduledRIRSyncJob
        from netbox_rir_manager.models import RIROrganization

        mock_arin("jobs", get_organization=arin_org("SCHEDLOG-ARIN", "Scheduled Log Org"))

        runner = make_runner(ScheduledRIRSyncJob)
        runner.job.user = None
        runner.run()

        org = RIROrganization.objects.get(handle="SCHEDLOG-ARIN")
        change = ObjectChange.objects.get(changed_object_id=org.pk, changed_object_type__model="rirorganization")
        assert change.user == default_key.user


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
