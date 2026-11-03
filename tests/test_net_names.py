import pytest

from netbox_rir_manager.net_names import ARIN_NET_NAME_MAX_LENGTH, build_net_name, to_ascii, validate_net_name


class TestBuildNetName:
    @pytest.mark.parametrize(
        "label, prefix, expected",
        [
            pytest.param("Test Tenant", "10.0.1.0/29", "TEST-TENANT-10-0-1-0-29", id="spaces-and-prefix"),
            pytest.param(
                "Adaptiv Networks Inc.",
                "50.21.160.32/29",
                "ADAPTIV-NETWORKS-INC-50-21-160-32-29",
                id="matches-existing-arin-record",
            ),
            pytest.param(
                "\u00c9nergie Qu\u00e9bec & Fils", "192.0.2.0/24", "ENERGIE-QUEBEC-FILS-192-0-2-0-24", id="accents"
            ),
            pytest.param("Acme", "2001:db8::/48", "ACME-2001-DB8-48", id="ipv6"),
            pytest.param("***", "192.0.2.0/24", "192-0-2-0-24", id="label-with-nothing-usable"),
        ],
    )
    def test_normalises_to_arin_rules(self, label, prefix, expected):
        assert build_net_name(label, prefix) == expected

    def test_truncates_label_and_keeps_prefix(self):
        name = build_net_name("Very Long Customer Name " * 4, "198.51.100.128/25")

        assert len(name) == ARIN_NET_NAME_MAX_LENGTH
        assert name.endswith("-198-51-100-128-25")
        assert "--" not in name


def test_to_ascii_transliterates_accents_and_drops_the_rest():
    assert to_ascii("Montr\u00e9al, Qu\u00e9bec \u2013 \u00c9cole") == "Montreal, Quebec  Ecole"


class TestValidateNetName:
    @pytest.mark.parametrize("value", ["ADAPTIV-NETWORKS-INC-50-21-160-32-29", "Metro Optic 01", "A" * 50])
    def test_accepts_arin_compatible_names(self, value):
        validate_net_name(value)

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("Test Tenant-10.0.1.0/29", id="dots-and-slash"),
            pytest.param("Qu\u00e9bec", id="non-ascii"),
        ],
    )
    def test_rejects_names_arin_refuses(self, value):
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            validate_net_name(value)


def test_form_field_enforces_arin_length_limit():
    from django.core.exceptions import ValidationError

    from netbox_rir_manager.fields import NetNameFormField

    field = NetNameFormField(required=False)
    assert field.clean("A" * 50) == "A" * 50
    with pytest.raises(ValidationError):
        field.clean("A" * 51)
