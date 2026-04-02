from django.db import models, transaction
from django.db.models import F
from partners.models import Partner
from products.models import Product
from django.utils import timezone
from decimal import Decimal
from company.models import CompanySetting
from datetime import timedelta


# ----------------------
# BASE INVOICE
# ----------------------

class BaseInvoice(models.Model):

    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        editable=False
    )

    invoice_date = models.DateField(default=timezone.now)

    importer = models.ForeignKey(
        Partner,
        related_name="%(class)s_importer",
        limit_choices_to={'partner_type': 'importer'},
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    end_user = models.ForeignKey(
        Partner,
        related_name="%(class)s_enduser",
        limit_choices_to={'partner_type': 'enduser'},
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    freight = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    vat_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        abstract = True

    # ----------------------
    # SUBTOTAL
    # ----------------------

    def subtotal(self):

        total = Decimal("0.00")

        for item in self.items.all():
            total += item.total_line()

        return total

    # ----------------------
    # VAT
    # ----------------------

    def vat_amount(self):
        return (self.subtotal() * self.vat_percent) / Decimal("100")

    # ----------------------
    # TOTAL
    # ----------------------

    def total_amount(self):

        return self.subtotal() + self.vat_amount() + self.freight - self.discount

    # ----------------------
    # AUTO NUMBER
    # ----------------------

    def save(self, *args, **kwargs):

        if not self.invoice_number:

            year = timezone.now().year

            last_invoice = self.__class__.objects.filter(
                invoice_number__startswith=f"FR/{year}"
            ).order_by("-id").first()

            if last_invoice:
                last_number = int(last_invoice.invoice_number.split("/")[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            self.invoice_number = f"FR/{year}/{new_number:04d}"

        super().save(*args, **kwargs)


# ----------------------
# PROFORMA INVOICE
# ----------------------

class ProformaInvoice(BaseInvoice):
    our_reference = models.CharField(max_length=100, blank=True)

    def ready_for_report(self):

        company = CompanySetting.objects.first()

        if not company:
            return False

        validity_days = company.proforma_validity

        expire_date = self.invoice_date + timedelta(days=validity_days)

        return timezone.now().date() >= expire_date

    # ----------------------
    # CONVERT TO COMMERCIAL
    # ----------------------

    def convert_to_commercial(self):
        existing_commercial = CommercialInvoice.objects.filter(
            our_reference=self.invoice_number
        ).first()

        if existing_commercial:
            return existing_commercial

        with transaction.atomic():
            commercial = CommercialInvoice.objects.create(
                invoice_date=self.invoice_date,
                importer=self.importer,
                end_user=self.end_user,
                freight=self.freight,
                discount=self.discount,
                vat_percent=self.vat_percent,
                our_reference=self.invoice_number
            )

            for item in self.items.select_related("product"):
                CommercialInvoiceItem.objects.create(
                    invoice=commercial,
                    product=item.product,
                    hs_code=item.hs_code,
                    quantity=item.quantity,
                    unit_price=item.unit_price
                )

            return commercial

    def __str__(self):
        return f"Proforma {self.invoice_number}"


# ----------------------
# PROFORMA ITEM
# ----------------------

class ProformaInvoiceItem(models.Model):

    invoice = models.ForeignKey(
        ProformaInvoice,
        related_name="items",
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        related_name="proforma_items",
        on_delete=models.PROTECT
    )

    hs_code = models.CharField(max_length=20, blank=True)

    quantity = models.IntegerField(default=0)

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    def save(self, *args, **kwargs):
        if not self.hs_code and self.product_id:
            self.hs_code = self.product.hs_code or "-"

        if not self.hs_code:
            self.hs_code = "-"

        super().save(*args, **kwargs)

    def total_line(self):

        return Decimal(self.quantity) * self.unit_price

    def __str__(self):

        return f"{self.product} - {self.invoice}"


# ----------------------
# COMMERCIAL INVOICE
# ----------------------

class CommercialInvoice(BaseInvoice):

    our_order_no = models.CharField(max_length=100, blank=True)

    our_reference = models.CharField(max_length=100, blank=True)

    def __str__(self):

        return f"Commercial {self.invoice_number}"


# ----------------------
# COMMERCIAL ITEM
# ----------------------

class CommercialInvoiceItem(models.Model):

    invoice = models.ForeignKey(
        CommercialInvoice,
        related_name="items",
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        related_name="commercial_items",
        on_delete=models.PROTECT
    )

    hs_code = models.CharField(max_length=20, blank=True)

    quantity = models.IntegerField(default=0)

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    def save(self, *args, **kwargs):
        if not self.hs_code and self.product_id:
            self.hs_code = self.product.hs_code or "-"

        if not self.hs_code:
            self.hs_code = "-"

        previous_item = None

        if self.pk:
            previous_item = CommercialInvoiceItem.objects.get(pk=self.pk)

        with transaction.atomic():
            super().save(*args, **kwargs)

            if previous_item:
                if previous_item.product_id == self.product_id:
                    quantity_diff = self.quantity - previous_item.quantity

                    if quantity_diff:
                        Product.objects.filter(pk=self.product_id).update(
                            unit_qty=F("unit_qty") - quantity_diff
                        )
                else:
                    Product.objects.filter(pk=previous_item.product_id).update(
                        unit_qty=F("unit_qty") + previous_item.quantity
                    )
                    Product.objects.filter(pk=self.product_id).update(
                        unit_qty=F("unit_qty") - self.quantity
                    )
            else:
                Product.objects.filter(pk=self.product_id).update(
                    unit_qty=F("unit_qty") - self.quantity
                )

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            Product.objects.filter(pk=self.product_id).update(
                unit_qty=F("unit_qty") + self.quantity
            )
            super().delete(*args, **kwargs)

    def total_line(self):

        return Decimal(self.quantity) * self.unit_price

    def __str__(self):

        return f"{self.product} - {self.invoice}"
