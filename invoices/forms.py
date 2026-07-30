from django import forms
from decimal import Decimal
from company.models import CompanySetting
from .models import ProformaInvoice, CommercialInvoice


class BaseInvoiceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = CompanySetting.objects.first()

        for field_name in ("freight", "discount", "vat_percent"):
            if field_name in self.fields:
                self.fields[field_name].required = False

        if company and not self.instance.pk:
            if "vat_percent" in self.fields:
                self.fields["vat_percent"].initial = company.vat_amount
            if "delivery_time" in self.fields:
                self.fields["delivery_time"].initial = company.delivery_time
            if "terms_conditions" in self.fields:
                self.fields["terms_conditions"].initial = company.terms_conditions

    def clean_freight(self):
        return self.cleaned_data.get("freight") or Decimal("0.00")

    def clean_discount(self):
        return self.cleaned_data.get("discount") or Decimal("0.00")

    def clean_vat_percent(self):
        value = self.cleaned_data.get("vat_percent")
        if value not in (None, ""):
            return value
        company = CompanySetting.objects.first()
        return company.vat_amount if company else Decimal("0.00")


class ProformaInvoiceForm(BaseInvoiceForm):
    class Meta:
        model = ProformaInvoice
        fields = [
            'invoice_number',
            'invoice_date',
            'importer',
            'end_user',
            'vat_percent',
            'our_reference',
            'price_for',
            'delivery_time',
            'terms_conditions',
            'freight',
            'discount',
        ]


class CommercialInvoiceForm(BaseInvoiceForm):
    class Meta:
        model = CommercialInvoice
        fields = [
            'invoice_number',
            'invoice_date',
            'importer',
            'end_user',
            'vat_percent',
            'our_order_no',
            'our_reference',
            'price_for',
            'dispatching_note',
            'packing_specification',
            'delivery_time',
            'terms_conditions',
            'freight',
            'discount',
        ]
