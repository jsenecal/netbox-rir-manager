"""Rename RIRSiteAddress → RIRAddress and centralize address fields.

Replaces the 5 inline address fields on RIROrganization, RIRContact, and
RIRCustomer with a FK to the (renamed) RIRAddress model.  Site becomes
nullable so the same model can store non-site addresses.
"""

import django.db.models.deletion
from django.db import migrations, models


def migrate_addresses_forward(apps, schema_editor):
    """Create RIRAddress rows from inline address fields and link them."""
    RIRAddress = apps.get_model("netbox_rir_manager", "RIRAddress")

    for model_name in ("RIROrganization", "RIRContact", "RIRCustomer"):
        Model = apps.get_model("netbox_rir_manager", model_name)
        for obj in Model.objects.all():
            has_data = any(
                [
                    obj.street_address,
                    obj.city,
                    obj.state_province,
                    obj.postal_code,
                    obj.country,
                ]
            )
            if not has_data:
                continue
            addr = RIRAddress.objects.create(
                street_address=obj.street_address,
                city=obj.city,
                state_province=obj.state_province,
                postal_code=obj.postal_code,
                country=obj.country,
            )
            obj.address = addr
            obj.save(update_fields=["address"])


class Migration(migrations.Migration):
    dependencies = [
        ("netbox_rir_manager", "0013_rircustomer"),
    ]

    operations = [
        # 1. Rename RIRSiteAddress → RIRAddress
        migrations.RenameModel(
            old_name="RIRSiteAddress",
            new_name="RIRAddress",
        ),
        # 2. Make site nullable
        migrations.AlterField(
            model_name="riraddress",
            name="site",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rir_address",
                to="dcim.site",
            ),
        ),
        # 3. Update model options
        migrations.AlterModelOptions(
            name="riraddress",
            options={
                "ordering": ["city", "country"],
                "verbose_name": "RIR address",
                "verbose_name_plural": "RIR addresses",
            },
        ),
        # 4. Add address FK to all three models
        migrations.AddField(
            model_name="rirorganization",
            name="address",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="rir_organizations",
                to="netbox_rir_manager.riraddress",
            ),
        ),
        migrations.AddField(
            model_name="rircontact",
            name="address",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="rir_contacts",
                to="netbox_rir_manager.riraddress",
            ),
        ),
        migrations.AddField(
            model_name="rircustomer",
            name="address",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="rir_customers",
                to="netbox_rir_manager.riraddress",
            ),
        ),
        # 5. Data migration
        migrations.RunPython(
            migrate_addresses_forward,
            migrations.RunPython.noop,
        ),
        # 6. Remove inline address fields (5 per model × 3 models = 15)
        migrations.RemoveField(model_name="rirorganization", name="street_address"),
        migrations.RemoveField(model_name="rirorganization", name="city"),
        migrations.RemoveField(model_name="rirorganization", name="state_province"),
        migrations.RemoveField(model_name="rirorganization", name="postal_code"),
        migrations.RemoveField(model_name="rirorganization", name="country"),
        migrations.RemoveField(model_name="rircontact", name="street_address"),
        migrations.RemoveField(model_name="rircontact", name="city"),
        migrations.RemoveField(model_name="rircontact", name="state_province"),
        migrations.RemoveField(model_name="rircontact", name="postal_code"),
        migrations.RemoveField(model_name="rircontact", name="country"),
        migrations.RemoveField(model_name="rircustomer", name="street_address"),
        migrations.RemoveField(model_name="rircustomer", name="city"),
        migrations.RemoveField(model_name="rircustomer", name="state_province"),
        migrations.RemoveField(model_name="rircustomer", name="postal_code"),
        migrations.RemoveField(model_name="rircustomer", name="country"),
    ]
