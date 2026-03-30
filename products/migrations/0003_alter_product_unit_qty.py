from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_alter_product_part_number"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="unit_qty",
            field=models.IntegerField(default=0),
        ),
    ]
