import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0225_gfk_indexes"),
        ("netbox_rir_manager", "0016_add_location_to_address"),
    ]

    operations = [
        migrations.AlterField(
            model_name="riraddress",
            name="site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rir_addresses",
                to="dcim.site",
            ),
        ),
        migrations.AlterField(
            model_name="riraddress",
            name="location",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="rir_address",
                to="dcim.location",
            ),
        ),
        migrations.AddConstraint(
            model_name="riraddress",
            constraint=models.UniqueConstraint(
                condition=models.Q(("location__isnull", True), ("site__isnull", False)),
                fields=("site",),
                name="unique_site_default_address",
            ),
        ),
    ]
