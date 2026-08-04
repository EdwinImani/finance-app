from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0022_proformainvoice_created_by_created_at"),
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
