from django.db import models

from financeapp.document_templates import (
    COMMERCIAL_INVOICE_TEMPLATE_CHOICES,
    COMMERCIAL_INVOICE_TEMPLATE_DEFAULT,
)


class CompanySetting(models.Model):

    CURRENCY_CHOICES = [
        ("EUR", "EUR - Euro"),
        ("USD", "USD - US Dollar"),
        ("CNY", "CNY - Chinese Yuan"),
        ("MAD", "MAD - Moroccan Dirham"),
        ("LBP", "LBP - Lebanese Pound"),
        ("IRR", "IRR - Iranian Rial"),
    ]

    company_logo = models.ImageField(
        upload_to="company/",
        null=True,
        blank=True
    )

    is_default = models.BooleanField(
        default=False,
        help_text="Use this profile for new documents unless another company is selected."
    )

    year = models.IntegerField(default=2026)

    company_name = models.CharField(max_length=255)
    president = models.CharField(max_length=255, blank=True)

    company_phone = models.CharField(max_length=100, blank=True)
    company_fax = models.CharField(max_length=100, blank=True)

    company_email = models.EmailField(blank=True)

    company_address = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)

    note = models.TextField(blank=True)

    footer_order = models.TextField(blank=True)

    siren = models.CharField(max_length=100, blank=True)
    vat_number = models.CharField(max_length=100, blank=True)

    bank = models.CharField(max_length=255, blank=True)
    iban = models.CharField(max_length=100, blank=True)
    bic = models.CharField(max_length=100, blank=True)

    footer_invoice = models.CharField(max_length=255, blank=True)

    invoice_note = models.TextField(blank=True)

    commercial_invoice_template = models.CharField(
        max_length=20,
        choices=COMMERCIAL_INVOICE_TEMPLATE_CHOICES,
        default=COMMERCIAL_INVOICE_TEMPLATE_DEFAULT,
        help_text="Default PDF template for commercial invoices issued by this company."
    )

    delivery_time = models.CharField(max_length=255, blank=True)

    terms_conditions = models.CharField(max_length=255, blank=True)

    # Validity Proforma
    proforma_validity = models.IntegerField(
        default=7,
        help_text="Number of days before proforma expires"
    )

    currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default="EUR"
    )

    vat_amount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20
    )

    class Meta:
        ordering = ("-is_default", "company_name", "id")

    @classmethod
    def get_default(cls):
        return cls.objects.filter(is_default=True).first() or cls.objects.first()

    def save(self, *args, **kwargs):
        if not self.pk and not CompanySetting.objects.exists():
            self.is_default = True

        old_logo_name = None

        if self.pk:
            old_instance = CompanySetting.objects.filter(pk=self.pk).first()

            if (
                old_instance and
                old_instance.company_logo and
                old_instance.company_logo.name != getattr(self.company_logo, "name", None)
            ):
                old_logo_name = old_instance.company_logo.name

        super().save(*args, **kwargs)

        if self.is_default:
            CompanySetting.objects.exclude(pk=self.pk).update(is_default=False)
        elif not CompanySetting.objects.filter(is_default=True).exists():
            CompanySetting.objects.filter(pk=self.pk).update(is_default=True)
            self.is_default = True

        if old_logo_name:
            self.company_logo.storage.delete(old_logo_name)

    def delete(self, *args, **kwargs):
        logo_name = self.company_logo.name if self.company_logo else None
        was_default = self.is_default

        super().delete(*args, **kwargs)

        if was_default and not CompanySetting.objects.filter(is_default=True).exists():
            replacement = CompanySetting.objects.order_by("company_name", "id").first()
            if replacement:
                replacement.is_default = True
                replacement.save(update_fields=["is_default"])

        if logo_name:
            self.company_logo.storage.delete(logo_name)

    def __str__(self):
        return self.company_name
