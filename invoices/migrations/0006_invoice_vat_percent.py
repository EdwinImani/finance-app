from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0004_remove_proformainvoiceitem_hs_code_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="commercialinvoice",
            name="vat_percent",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=5),
        ),
        migrations.AddField(
            model_name="proformainvoice",
            name="vat_percent",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=5),
        ),
    ]
