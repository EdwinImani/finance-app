from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("purchase", "0008_purchaseorder_created_by_created_at"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="purchaseorder",
            options={
                "permissions": (
                    (
                        "view_purchase_order_reports",
                        "Can access Purchase Order reports",
                    ),
                ),
            },
        ),
    ]
