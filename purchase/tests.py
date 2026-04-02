from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from company.models import CompanySetting
from products.models import Product
from purchase.admin import PurchaseOrderAdminForm


class ProductInfoViewTests(TestCase):

    def test_product_info_returns_invoice_and_purchase_fields(self):
        product = Product.objects.create(
            description="Produit API",
            part_number="API-001",
            hs_code="8471.30",
            note="Note produit",
            unit_qty=12,
            purchase_price=Decimal("5.50"),
            sale_price=Decimal("9.90"),
        )

        response = self.client.get(reverse("product_info", args=[product.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "description": "Produit API",
                "part_number": "API-001",
                "hs_code": "8471.30",
                "note": "Note produit",
                "unit_qty": "12",
                "unit_price": "5.50",
                "sale_price": "9.90",
            },
        )


class PurchaseOrderAdminFormTests(TestCase):

    def test_vat_percent_uses_company_setting_as_initial_value(self):
        CompanySetting.objects.create(
            company_name="Societe Test",
            vat_amount=Decimal("20.00"),
        )

        form = PurchaseOrderAdminForm()

        self.assertEqual(form.fields["vat_percent"].initial, Decimal("20.00"))
