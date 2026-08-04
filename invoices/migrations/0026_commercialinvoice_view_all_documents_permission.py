from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0025_remove_proformainvoice_creator_columns"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="commercialinvoice",
            options={
                "permissions": (
                    (
                        "view_all_documents",
                        "Can view all users' invoices and purchase orders",
                    ),
                ),
            },
        ),
    ]
