from django.db import models


class CompanySetting(models.Model):

    CURRENCY_CHOICES = [
        ("EUR", "Euro"),
        ("USD", "USD"),
        ("CNY", "Yuan"),
        ("MAD", "Dirham"),
        ("LBP", "Lear"),
        ("IRR", "Rls"),
    ]

    company_logo = models.ImageField(
        upload_to="company/",
        null=True,
        blank=True
    )

    year = models.IntegerField(default=2026)

    company_name = models.CharField(max_length=255)

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

    def save(self, *args, **kwargs):
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

        if old_logo_name:
            self.company_logo.storage.delete(old_logo_name)

    def delete(self, *args, **kwargs):
        logo_name = self.company_logo.name if self.company_logo else None

        super().delete(*args, **kwargs)

        if logo_name:
            self.company_logo.storage.delete(logo_name)

    def __str__(self):
        return self.company_name
