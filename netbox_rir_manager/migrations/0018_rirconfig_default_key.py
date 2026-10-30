import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Count


def default_single_keys(apps, schema_editor):
    """Keep the scheduled sync running where it is unambiguous whose key it used.

    The scheduled sync now runs only with a config's default key. A config with exactly one
    key was necessarily syncing with it, so that key becomes the default; configs with several
    keys are left for an administrator to choose.
    """
    RIRConfig = apps.get_model("netbox_rir_manager", "RIRConfig")
    RIRUserKey = apps.get_model("netbox_rir_manager", "RIRUserKey")

    single_key_configs = RIRConfig.objects.annotate(key_count=Count("user_keys")).filter(key_count=1)
    for config in single_key_configs:
        config.default_key = RIRUserKey.objects.get(rir_config=config)
        config.save(update_fields=["default_key"])


class Migration(migrations.Migration):
    dependencies = [
        ("netbox_rir_manager", "0017_site_fk_location_onetoone"),
    ]

    operations = [
        migrations.AddField(
            model_name="rirconfig",
            name="default_key",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="netbox_rir_manager.riruserkey",
            ),
        ),
        migrations.RunPython(default_single_keys, migrations.RunPython.noop),
    ]
