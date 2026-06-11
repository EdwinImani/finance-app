from django.db import migrations, models


def populate_invoice_item_part_numbers(apps, schema_editor):
    ProformaInvoiceItem = apps.get_model("invoices", "ProformaInvoiceItem")
    CommercialInvoiceItem = apps.get_model("invoices", "CommercialInvoiceItem")

    for model in (ProformaInvoiceItem, CommercialInvoiceItem):
        for item in model.objects.select_related("product"):
            part_number = ""
            if item.product_id:
                part_number = item.product.part_number or ""

            if part_number:
                item.part_number = part_number
                item.save(update_fields=["part_number"])


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0013_alter_commercialinvoiceitem_product_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="commercialinvoiceitem",
            name="part_number",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="proformainvoiceitem",
            name="part_number",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.RunPython(populate_invoice_item_part_numbers, migrations.RunPython.noop),
    ]
