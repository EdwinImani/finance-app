from django.db import migrations, models


def copy_invoice_hs_code_to_items(apps, schema_editor):
    ProformaInvoice = apps.get_model("invoices", "ProformaInvoice")
    ProformaInvoiceItem = apps.get_model("invoices", "ProformaInvoiceItem")
    Product = apps.get_model("products", "Product")

    for item in ProformaInvoiceItem.objects.select_related("invoice", "product"):
        hs_code = ""

        if item.invoice_id:
            invoice = ProformaInvoice.objects.get(pk=item.invoice_id)
            hs_code = getattr(invoice, "hs_code", "") or ""

        if not hs_code and item.product_id:
            product = Product.objects.get(pk=item.product_id)
            hs_code = product.hs_code or ""

        item.hs_code = hs_code or "-"
        item.save(update_fields=["hs_code"])


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0004_product_hs_code"),
        ("invoices", "0006_invoice_vat_percent"),
    ]

    operations = [
        migrations.AddField(
            model_name="proformainvoiceitem",
            name="hs_code",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.RunPython(copy_invoice_hs_code_to_items, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="proformainvoice",
            name="hs_code",
        ),
    ]
