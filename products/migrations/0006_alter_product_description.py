from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0005_remove_product_unit_price"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="description",
            field=models.CharField(max_length=255),
        ),
    ]
