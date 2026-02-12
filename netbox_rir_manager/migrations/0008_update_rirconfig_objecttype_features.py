from django.db import migrations


def update_objecttype_features(apps, schema_editor):
    """Refresh the ObjectType features for RIRConfig to include 'jobs'."""
    ObjectType = apps.get_model("core", "ObjectType")
    try:
        ot = ObjectType.objects.get(app_label="netbox_rir_manager", model="rirconfig")
        if "jobs" not in ot.features:
            ot.features.append("jobs")
            ot.save(update_fields=["features"])
    except ObjectType.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0018_concrete_objecttype"),
        ("netbox_rir_manager", "0007_alter_rirconfig_api_url"),
    ]

    operations = [
        migrations.RunPython(update_objecttype_features, migrations.RunPython.noop),
    ]
