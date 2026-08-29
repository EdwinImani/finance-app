from django.db import migrations, models
import django.db.models.deletion


def attach_default_company_to_commercial_invoices(apps, schema_editor):
    CompanySetting = apps.get_model("company", "CompanySetting")
    CommercialInvoice = apps.get_model("invoices", "CommercialInvoice")

    company = (
        CompanySetting.objects.filter(is_default=True).first()
        or CompanySetting.objects.order_by("id").first()
    )
    if not company:
        return

    CommercialInvoice.objects.filter(issuing_company__isnull=True).update(
        issuing_company=company,
        pdf_template=company.commercial_invoice_template or "classic",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("company", "0004_companysetting_multi_company_defaults"),
        ("invoices", "0028_split_report_access_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="commercialinvoice",
            name="issuing_company",
            field=models.ForeignKey(
                blank=True,
                help_text="Company profile, address, logo, and bank details used on this invoice.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="commercial_invoices",
                to="company.companysetting",
            ),
        ),
        migrations.AddField(
            model_name="commercialinvoice",
            name="pdf_template",
            field=models.CharField(
                choices=[
                    ("classic", "Classic orange"),
                    ("blue", "Blue letterhead"),
                    ("green", "Green export"),
                    ("mono", "Minimal monochrome"),
                ],
                default="classic",
                help_text="Visual PDF template used for this commercial invoice.",
                max_length=20,
            ),
        ),
        migrations.RunPython(
            attach_default_company_to_commercial_invoices,
            migrations.RunPython.noop,
        ),
    ]
