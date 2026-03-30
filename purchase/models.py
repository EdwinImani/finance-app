from django.db import models
from django.utils import timezone
from decimal import Decimal
from partners.models import Partner
from products.models import Product


# ----------------------
# PURCHASE ORDER
# ----------------------

class PurchaseOrder(models.Model):

    purchase_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        editable=False
    )

    purchase_date = models.DateField(
        default=timezone.now
    )

    seller = models.ForeignKey(
        Partner,
        related_name="purchase_orders_as_seller",
        limit_choices_to={'partner_type': 'seller'},
        on_delete=models.PROTECT
    )

    requester = models.ForeignKey(
        Partner,
        related_name="purchase_orders_as_requester",
        limit_choices_to={'partner_type': 'requester'},
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    sent_by = models.CharField(max_length=255, blank=True)
    shipment = models.CharField(max_length=255, blank=True)

    freight = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vat_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    sales_condition = models.CharField(max_length=255, blank=True)
    payment_condition = models.CharField(max_length=255, blank=True)
    delivery_terms = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.purchase_number or "Purchase Order"

    # ----------------------
    # GROSS VALUE
    # ----------------------

    def gross_value(self):
        total = Decimal("0.00")

        for item in self.items.all():
            total += item.total_line()

        return total

    # ----------------------
    # VAT AMOUNT
    # ----------------------

    def vat_amount(self):
        return (self.gross_value() * self.vat_percent) / Decimal("100")

    # ----------------------
    # TOTAL AMOUNT
    # ----------------------

    def total_amount(self):
        return self.gross_value() + self.vat_amount() + self.freight

    # ----------------------
    # AUTO NUMBER
    # ----------------------

    def save(self, *args, **kwargs):

        if not self.purchase_number:
            year = self.purchase_date.year

            last_po = PurchaseOrder.objects.filter(
                purchase_number__startswith=f"PO/{year}"
            ).order_by("-id").first()

            if last_po:
                last_number = int(last_po.purchase_number.split("-")[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            self.purchase_number = f"PO/{year}-{new_number:04d}"

        super().save(*args, **kwargs)


# ----------------------
# PURCHASE ORDER ITEM
# ----------------------

class PurchaseOrderItem(models.Model):

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        related_name="items",
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )

    description = models.CharField(
        max_length=255,
        blank=True
    )

    part_number = models.CharField(
        max_length=255,
        blank=True
    )

    quantity = models.IntegerField(default=1)

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # ----------------------
    # TOTAL LINE
    # ----------------------

    def total_line(self):
        return Decimal(self.quantity) * self.unit_price

    total_line.short_description = "Total"

    # ----------------------
    # AUTO FILL ON SAVE
    # ----------------------

    def save(self, *args, **kwargs):
        if self.product:
            if not self.description:
                self.description = self.product.description

            if not self.unit_price:
                self.unit_price = self.product.purchase_price

        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.product)