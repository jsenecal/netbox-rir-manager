import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("netbox_rir_manager", "0001_initial"),
        ("ipam", "0086_gfk_indexes"),
    ]

    operations = [
        # 1. Rename the model
        migrations.RenameModel(
            old_name="RIRAccount",
            new_name="RIRConfig",
        ),
        # 2. Rename FK fields on child models
        migrations.RenameField(
            model_name="rirorganization",
            old_name="account",
            new_name="rir_config",
        ),
        migrations.RenameField(
            model_name="rircontact",
            old_name="account",
            new_name="rir_config",
        ),
        migrations.RenameField(
            model_name="rirnetwork",
            old_name="account",
            new_name="rir_config",
        ),
        migrations.RenameField(
            model_name="rirsynclog",
            old_name="account",
            new_name="rir_config",
        ),
        # 3. Remove the api_key field
        migrations.RemoveField(
            model_name="rirconfig",
            name="api_key",
        ),
        # 4. Update the unique constraint name
        migrations.RemoveConstraint(
            model_name="rirconfig",
            name="unique_rir_account_name",
        ),
        migrations.AddConstraint(
            model_name="rirconfig",
            constraint=models.UniqueConstraint(fields=("rir", "name"), name="unique_rir_config_name"),
        ),
        # 5. Update the related_name on the rir FK
        migrations.AlterField(
            model_name="rirconfig",
            name="rir",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rir_configs",
                to="ipam.rir",
            ),
        ),
    ]
