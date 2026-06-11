from django.db import migrations, models


def populate_purchase_item_hs_codes(apps, schema_editor):
    PurchaseOrderItem = apps.get_model("purchase", "PurchaseOrderItem")

    for item in PurchaseOrderItem.objects.select_related("product"):
        hs_code = ""
        if item.product_id:
            hs_code = item.product.hs_code or ""

        item.hs_code = hs_code or "-"
        item.save(update_fields=["hs_code"])


class Migration(migrations.Migration):

    dependencies = [
        ("purchase", "0005_alter_purchaseorderitem_product"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseorderitem",
            name="hs_code",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.RunPython(populate_purchase_item_hs_codes, migrations.RunPython.noop),
    ]
