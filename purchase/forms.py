from django import forms
from partners.models import Partner
from products.models import Product


class PurchaseReportForm(forms.Form):

    year = forms.IntegerField(
        required=False,
        label="Year"
    )

    date_from = forms.DateField(
        required=False,
        label="From",
        widget=forms.DateInput(attrs={"type": "date"})
    )

    date_to = forms.DateField(
        required=False,
        label="To",
        widget=forms.DateInput(attrs={"type": "date"})
    )

    seller = forms.ModelChoiceField(
        queryset=Partner.objects.filter(partner_type="seller"),
        required=False,
        label="Seller"
    )

    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        required=False,
        label="Product"
    )