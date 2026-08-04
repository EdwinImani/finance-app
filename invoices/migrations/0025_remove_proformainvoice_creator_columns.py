from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0024_proformainvoice_creator_audit"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="proformainvoice",
            name="created_at",
        ),
        migrations.RemoveField(
            model_name="proformainvoice",
            name="created_by",
        ),
    ]
