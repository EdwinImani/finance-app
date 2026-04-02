from django import forms
from company.models import CompanySetting
from .models import ProformaInvoice, CommercialInvoice


class BaseInvoiceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = CompanySetting.objects.first()

        if company and not self.instance.pk and "vat_percent" in self.fields:
            self.fields["vat_percent"].initial = company.vat_amount


class ProformaInvoiceForm(BaseInvoiceForm):
    class Meta:
        model = ProformaInvoice
        fields = [
            'invoice_date',
            'importer',
            'end_user',
            'vat_percent',
            'our_reference',
            'freight',
            'discount',
        ]


class CommercialInvoiceForm(BaseInvoiceForm):
    class Meta:
        model = CommercialInvoice
        fields = [
            'invoice_date',
            'importer',
            'end_user',
            'vat_percent',
            'our_order_no',
            'our_reference',
            'freight',
            'discount',
        ]
