from django.db import migrations


def normalize_invoice_numbers(apps, schema_editor):
    for model_name in ("ProformaInvoice", "CommercialInvoice"):
        invoice_model = apps.get_model("invoices", model_name)
        for invoice in invoice_model.objects.filter(invoice_number__contains="/").iterator():
            normalized_number = invoice.invoice_number.replace("/", "-")
            if invoice_model.objects.exclude(pk=invoice.pk).filter(
                invoice_number=normalized_number
            ).exists():
                continue
            invoice_model.objects.filter(pk=invoice.pk).update(
                invoice_number=normalized_number
            )


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0019_alter_commercialinvoicepacking_dimension_height_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_invoice_numbers, migrations.RunPython.noop),
    ]
