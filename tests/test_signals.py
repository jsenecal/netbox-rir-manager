import pytest


@pytest.mark.django_db
class TestAutoLinkSignal:
    def test_auto_links_aggregate_on_save(self, rir_config, rir):
        from ipam.models import Aggregate
        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-192-0-2-0-1",
            net_name="EXAMPLE-NET",
            raw_data={
                "net_blocks": [
                    {"start_address": "192.0.2.0", "cidr_length": 24, "type": "DS"}
                ]
            },
        )
        net.refresh_from_db()
        assert net.aggregate == agg

    def test_auto_links_prefix_on_save(self, rir_config, rir):
        from ipam.models import Prefix
        from netbox_rir_manager.models import RIRNetwork

        pfx = Prefix.objects.create(prefix="10.0.0.0/8")
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-10-0-0-0-1",
            net_name="TEN-NET",
            raw_data={
                "net_blocks": [
                    {"start_address": "10.0.0.0", "cidr_length": 8, "type": "DS"}
                ]
            },
        )
        net.refresh_from_db()
        assert net.prefix == pfx

    def test_auto_link_does_not_overwrite_existing(self, rir_config, rir):
        from ipam.models import Aggregate
        from netbox_rir_manager.models import RIRNetwork

        agg1 = Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
        agg2 = Aggregate.objects.create(prefix="10.0.0.0/8", rir=rir)
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-192-0-2-0-1",
            net_name="EXAMPLE-NET",
            aggregate=agg2,  # manually set to different aggregate
            raw_data={
                "net_blocks": [
                    {"start_address": "192.0.2.0", "cidr_length": 24, "type": "DS"}
                ]
            },
        )
        net.refresh_from_db()
        assert net.aggregate == agg2  # should NOT be overwritten

    def test_auto_link_disabled_by_setting(self, rir_config, rir, settings):
        from ipam.models import Aggregate
        from netbox_rir_manager.models import RIRNetwork

        settings.PLUGINS_CONFIG = {"netbox_rir_manager": {"auto_link_networks": False}}
        Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-DISABLED-1",
            net_name="DISABLED-NET",
            raw_data={
                "net_blocks": [
                    {"start_address": "192.0.2.0", "cidr_length": 24, "type": "DS"}
                ]
            },
        )
        net.refresh_from_db()
        assert net.aggregate is None

    def test_no_match_does_nothing(self, rir_config):
        from netbox_rir_manager.models import RIRNetwork

        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-NOMATCH-1",
            net_name="NO-MATCH-NET",
            raw_data={
                "net_blocks": [
                    {"start_address": "172.16.0.0", "cidr_length": 12, "type": "DS"}
                ]
            },
        )
        net.refresh_from_db()
        assert net.aggregate is None
        assert net.prefix is None

    def test_empty_raw_data_does_nothing(self, rir_config):
        from netbox_rir_manager.models import RIRNetwork

        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-EMPTY-1",
            net_name="EMPTY-NET",
            raw_data={},
        )
        net.refresh_from_db()
        assert net.aggregate is None
        assert net.prefix is None
