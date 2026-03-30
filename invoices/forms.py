from django import forms
from .models import ProformaInvoice, CommercialInvoice


class ProformaInvoiceForm(forms.ModelForm):
    class Meta:
        model = ProformaInvoice
        fields = [
            'invoice_date',
            'importer',
            'end_user',
            'hs_code',
            'our_reference',
            'freight',
            'discount',
        ]


class CommercialInvoiceForm(forms.ModelForm):
    class Meta:
        model = CommercialInvoice
        fields = [
            'invoice_date',
            'importer',
            'end_user',
            'our_order_no',
            'our_reference',
            'freight',
            'discount',
        ]
