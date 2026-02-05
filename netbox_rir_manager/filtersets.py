import django_filters
from django.contrib.auth import get_user_model
from ipam.models import RIR
from netbox.filtersets import NetBoxModelFilterSet
from tenancy.models import Contact

from netbox_rir_manager.models import RIRConfig, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog, RIRUserKey


class RIRConfigFilterSet(NetBoxModelFilterSet):
    rir_id = django_filters.ModelMultipleChoiceFilter(queryset=RIR.objects.all(), label="RIR")
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = RIRConfig
        fields = ("id", "name", "rir_id", "is_active", "org_handle")

    def search(self, queryset, name, value):
        return queryset.filter(name__icontains=value)


class RIROrganizationFilterSet(NetBoxModelFilterSet):
    rir_config_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRConfig.objects.all(), label="RIR Config")

    class Meta:
        model = RIROrganization
        fields = ("id", "handle", "name", "rir_config_id", "country")

    def search(self, queryset, name, value):
        return queryset.filter(handle__icontains=value) | queryset.filter(name__icontains=value)


class RIRContactFilterSet(NetBoxModelFilterSet):
    rir_config_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRConfig.objects.all(), label="RIR Config")
    contact_type = django_filters.CharFilter()
    organization_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIROrganization.objects.all(), label="Organization"
    )
    contact_id = django_filters.ModelMultipleChoiceFilter(queryset=Contact.objects.all(), label="Contact")

    class Meta:
        model = RIRContact
        fields = ("id", "handle", "contact_type", "rir_config_id", "organization_id", "contact_id")

    def search(self, queryset, name, value):
        return queryset.filter(handle__icontains=value) | queryset.filter(last_name__icontains=value)


class RIRNetworkFilterSet(NetBoxModelFilterSet):
    rir_config_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRConfig.objects.all(), label="RIR Config")
    organization_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIROrganization.objects.all(), label="Organization"
    )

    class Meta:
        model = RIRNetwork
        fields = ("id", "handle", "net_name", "rir_config_id", "organization_id")

    def search(self, queryset, name, value):
        return queryset.filter(handle__icontains=value) | queryset.filter(net_name__icontains=value)


class RIRSyncLogFilterSet(NetBoxModelFilterSet):
    rir_config_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRConfig.objects.all(), label="RIR Config")
    operation = django_filters.CharFilter()
    status = django_filters.CharFilter()

    class Meta:
        model = RIRSyncLog
        fields = ("id", "rir_config_id", "operation", "status", "object_type")

    def search(self, queryset, name, value):
        return queryset.filter(object_handle__icontains=value) | queryset.filter(message__icontains=value)


class RIRUserKeyFilterSet(NetBoxModelFilterSet):
    user = django_filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all(), label="User")
    rir_config_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRConfig.objects.all(), label="RIR Config")

    class Meta:
        model = RIRUserKey
        fields = ("id", "user", "rir_config_id")

    def search(self, queryset, name, value):
        return queryset.filter(user__username__icontains=value)
