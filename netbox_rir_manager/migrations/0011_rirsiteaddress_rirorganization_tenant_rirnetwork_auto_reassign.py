import django.db.models.deletion
import taggit.managers
import utilities.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0001_initial'),
        ('extras', '0001_initial'),
        ('tenancy', '0001_initial'),
        ('netbox_rir_manager', '0010_add_rircontact_address_fields'),
    ]

    operations = [
        # Create RIRSiteAddress model
        migrations.CreateModel(
            name='RIRSiteAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ('street_address', models.TextField(blank=True, default='')),
                ('city', models.CharField(blank=True, default='', max_length=100)),
                ('state_province', models.CharField(blank=True, default='', help_text='ISO-3166-2 subdivision code (e.g. NY, QC)', max_length=10)),
                ('postal_code', models.CharField(blank=True, default='', max_length=20)),
                ('country', models.CharField(blank=True, default='', help_text='ISO-3166-1 alpha-2 country code', max_length=2)),
                ('raw_geocode', models.JSONField(blank=True, default=dict, help_text='Full geocoder response for debugging')),
                ('auto_resolved', models.BooleanField(default=False, help_text='True if geocoded, False if manually entered')),
                ('last_resolved', models.DateTimeField(blank=True, null=True)),
                ('site', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='rir_address', to='dcim.site')),
                ('tags', taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'verbose_name': 'RIR site address',
                'verbose_name_plural': 'RIR site addresses',
                'ordering': ['site__name'],
            },
        ),
        # Add tenant FK to RIROrganization
        migrations.AddField(
            model_name='rirorganization',
            name='tenant',
            field=models.ForeignKey(
                blank=True,
                help_text='Link to a NetBox Tenant for automatic detailed reassignment',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='rir_organizations',
                to='tenancy.tenant',
            ),
        ),
        # Add auto_reassign to RIRNetwork
        migrations.AddField(
            model_name='rirnetwork',
            name='auto_reassign',
            field=models.BooleanField(
                default=False,
                help_text='Automatically reassign child prefixes at ARIN when they get a Site and Tenant',
            ),
        ),
    ]
