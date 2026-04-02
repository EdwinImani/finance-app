from django.db import models


class Product(models.Model):

    description = models.CharField(
        max_length=255,
        unique=True
    )

    part_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )

    hs_code = models.CharField(
        max_length=20,
        blank=True
    )

    note = models.CharField(
        max_length=255,
        blank=True
    )

    unit_qty = models.IntegerField(
        default=0
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    class Meta:
        ordering = ["description"]

    def admin_label(self):
        if self.part_number:
            return f"{self.part_number} - {self.description}"

        return self.description

    def __str__(self):
        return self.admin_label()
