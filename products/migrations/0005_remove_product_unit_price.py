from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0004_product_hs_code"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="product",
            name="unit_price",
        ),
    ]
