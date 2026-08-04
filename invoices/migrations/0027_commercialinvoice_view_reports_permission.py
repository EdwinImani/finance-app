from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "invoices",
            "0026_commercialinvoice_view_all_documents_permission",
        ),
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
                    (
                        "view_reports",
                        "Can access invoice and purchase order reports",
                    ),
                ),
            },
        ),
    ]
