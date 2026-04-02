from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0003_alter_product_unit_qty"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="hs_code",
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
