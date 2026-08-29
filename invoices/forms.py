from django import forms
from decimal import Decimal
from company.models import CompanySetting
from financeapp.document_templates import COMMERCIAL_INVOICE_TEMPLATE_DEFAULT
from .models import ProformaInvoice, CommercialInvoice


class BaseInvoiceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = self._get_initial_company()

        for field_name in ("freight", "discount", "vat_percent"):
            if field_name in self.fields:
                self.fields[field_name].required = False
        if "pdf_template" in self.fields:
            self.fields["pdf_template"].required = False

        if company and not self.instance.pk:
            if "issuing_company" in self.fields:
                self.fields["issuing_company"].initial = company.pk
            if "pdf_template" in self.fields:
                self.fields["pdf_template"].initial = (
                    company.commercial_invoice_template or COMMERCIAL_INVOICE_TEMPLATE_DEFAULT
                )
            if "vat_percent" in self.fields:
                self.fields["vat_percent"].initial = company.vat_amount
            if "delivery_time" in self.fields:
                self.fields["delivery_time"].initial = company.delivery_time
            if "terms_conditions" in self.fields:
                self.fields["terms_conditions"].initial = company.terms_conditions

    def _get_initial_company(self):
        if getattr(self.instance, "issuing_company_id", None):
            return self.instance.issuing_company
        return CompanySetting.get_default()

    def _get_cleaned_company(self):
        return self.cleaned_data.get("issuing_company") or CompanySetting.get_default()

    def clean_freight(self):
        return self.cleaned_data.get("freight") or Decimal("0.00")

    def clean_discount(self):
        return self.cleaned_data.get("discount") or Decimal("0.00")

    def clean_vat_percent(self):
        value = self.cleaned_data.get("vat_percent")
        if value not in (None, ""):
            return value
        company = self._get_cleaned_company()
        return company.vat_amount if company else Decimal("0.00")

    def clean_issuing_company(self):
        return self.cleaned_data.get("issuing_company") or CompanySetting.get_default()

    def clean_pdf_template(self):
        value = self.cleaned_data.get("pdf_template")
        if value:
            return value
        company = self._get_cleaned_company()
        if company and company.commercial_invoice_template:
            return company.commercial_invoice_template
        return COMMERCIAL_INVOICE_TEMPLATE_DEFAULT


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
            'issuing_company',
            'pdf_template',
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
