from django.db import models


class Product(models.Model):

    description = models.TextField()

    part_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
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
        # Keep autocomplete labels on one line while retaining the original
        # formatting in the saved description for document generation.
        description_label = " ".join(self.description.split())
        if self.part_number:
            return f"#{self.pk} - {description_label} - {self.part_number}" if self.pk else f"{description_label} - {self.part_number}"
        if self.pk:
            return f"#{self.pk} - {description_label}"
        return description_label

    def __str__(self):
        return self.admin_label()
