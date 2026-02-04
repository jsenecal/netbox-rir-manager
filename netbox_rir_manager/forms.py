from django import forms
from ipam.models import RIR
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from utilities.forms.rendering import FieldSet

from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization


class RIRAccountForm(NetBoxModelForm):
    rir = DynamicModelChoiceField(queryset=RIR.objects.all())

    fieldsets = (
        FieldSet("rir", "name", "api_key", "api_url", "org_handle", "is_active", name="RIR Account"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIRAccount
        fields = ("rir", "name", "api_key", "api_url", "org_handle", "is_active", "tags")
        widgets = {
            "api_key": forms.PasswordInput(render_value=True),
        }


class RIRAccountFilterForm(NetBoxModelFilterSetForm):
    model = RIRAccount
    rir_id = DynamicModelMultipleChoiceField(queryset=RIR.objects.all(), required=False, label="RIR")
    is_active = forms.NullBooleanField(required=False)


class RIROrganizationForm(NetBoxModelForm):
    account = DynamicModelChoiceField(queryset=RIRAccount.objects.all())

    fieldsets = (
        FieldSet("account", "handle", "name", name="Organization"),
        FieldSet("street_address", "city", "state_province", "postal_code", "country", name="Address"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIROrganization
        fields = (
            "account",
            "handle",
            "name",
            "street_address",
            "city",
            "state_province",
            "postal_code",
            "country",
            "tags",
        )


class RIROrganizationFilterForm(NetBoxModelFilterSetForm):
    model = RIROrganization
    account_id = DynamicModelMultipleChoiceField(queryset=RIRAccount.objects.all(), required=False, label="Account")
    country = forms.CharField(required=False)


class RIRContactForm(NetBoxModelForm):
    account = DynamicModelChoiceField(queryset=RIRAccount.objects.all())
    organization = DynamicModelChoiceField(queryset=RIROrganization.objects.all(), required=False)

    fieldsets = (
        FieldSet("account", "handle", "contact_type", name="Contact"),
        FieldSet("first_name", "last_name", "company_name", "email", "phone", name="Details"),
        FieldSet("organization", name="Organization"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIRContact
        fields = (
            "account",
            "handle",
            "contact_type",
            "first_name",
            "last_name",
            "company_name",
            "email",
            "phone",
            "organization",
            "tags",
        )


class RIRContactFilterForm(NetBoxModelFilterSetForm):
    model = RIRContact
    account_id = DynamicModelMultipleChoiceField(queryset=RIRAccount.objects.all(), required=False, label="Account")
    contact_type = forms.CharField(required=False)
    organization_id = DynamicModelMultipleChoiceField(
        queryset=RIROrganization.objects.all(), required=False, label="Organization"
    )


class RIRNetworkForm(NetBoxModelForm):
    account = DynamicModelChoiceField(queryset=RIRAccount.objects.all())
    organization = DynamicModelChoiceField(queryset=RIROrganization.objects.all(), required=False)

    fieldsets = (
        FieldSet("account", "handle", "net_name", "organization", name="Network"),
        FieldSet("aggregate", "prefix", name="NetBox Links"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIRNetwork
        fields = ("account", "handle", "net_name", "organization", "aggregate", "prefix", "tags")


class RIRNetworkFilterForm(NetBoxModelFilterSetForm):
    model = RIRNetwork
    account_id = DynamicModelMultipleChoiceField(queryset=RIRAccount.objects.all(), required=False, label="Account")
    organization_id = DynamicModelMultipleChoiceField(
        queryset=RIROrganization.objects.all(), required=False, label="Organization"
    )
