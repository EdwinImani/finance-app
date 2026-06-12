from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from company.models import CompanySetting
from products.models import Product
from purchase.admin import PurchaseOrderAdminForm
from purchase.models import PurchaseOrder, PurchaseOrderItem


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
                "sale_price": "9.90",
                "purchase_price": "5.50",
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


class PurchaseOrderItemTests(TestCase):

    def test_item_uses_product_hs_code_and_part_number_by_default(self):
        product = Product.objects.create(
            description="Produit PO",
            part_number="PO-001",
            hs_code="8504.40",
            purchase_price=Decimal("12.50"),
        )
        purchase_order = PurchaseOrder.objects.create()

        item = PurchaseOrderItem.objects.create(
            purchase_order=purchase_order,
            product=product,
            quantity=2,
        )

        self.assertEqual(item.description, "Produit PO")
        self.assertEqual(item.part_number, "PO-001")
        self.assertEqual(item.hs_code, "8504.40")
        self.assertEqual(item.unit_price, Decimal("12.50"))
