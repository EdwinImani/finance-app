from django.db import migrations, models


def mark_first_company_as_default(apps, schema_editor):
    CompanySetting = apps.get_model("company", "CompanySetting")
    first_company = CompanySetting.objects.order_by("id").first()
    if first_company:
        CompanySetting.objects.filter(pk=first_company.pk).update(is_default=True)


class Migration(migrations.Migration):

    dependencies = [
        ("company", "0003_companysetting_president"),
    ]

    operations = [
        migrations.AddField(
            model_name="companysetting",
            name="is_default",
            field=models.BooleanField(
                default=False,
                help_text="Use this profile for new documents unless another company is selected.",
            ),
        ),
        migrations.AddField(
            model_name="companysetting",
            name="commercial_invoice_template",
            field=models.CharField(
                choices=[
                    ("classic", "Classic orange"),
                    ("blue", "Blue letterhead"),
                    ("green", "Green export"),
                    ("mono", "Minimal monochrome"),
                ],
                default="classic",
                help_text="Default PDF template for commercial invoices issued by this company.",
                max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name="companysetting",
            options={"ordering": ("-is_default", "company_name", "id")},
        ),
        migrations.RunPython(mark_first_company_as_default, migrations.RunPython.noop),
    ]
