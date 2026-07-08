from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from company.models import CompanySetting
from products.models import Product
from purchase.admin import PurchaseOrderAdminForm
from purchase.models import PurchaseOrder, PurchaseOrderItem


class ProductInfoViewTests(TestCase):

    def test_product_info_returns_invoice_and_purchase_fields(self):
        user = get_user_model().objects.create_user(
            username="staff",
            password="password123",
            is_staff=True,
        )
        product = Product.objects.create(
            description="Produit API",
            part_number="API-001",
            hs_code="8471.30",
            note="Note produit",
            unit_qty=12,
            purchase_price=Decimal("5.50"),
            sale_price=Decimal("9.90"),
        )

        anonymous_response = self.client.get(reverse("product_info", args=[product.id]))
        self.assertEqual(anonymous_response.status_code, 302)

        self.client.force_login(user)
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

    def test_item_price_change_does_not_update_product_purchase_price(self):
        product = Product.objects.create(
            description="Produit Prix PO",
            part_number="PO-PRICE-001",
            hs_code="8504.40",
            purchase_price=Decimal("12.50"),
        )
        purchase_order = PurchaseOrder.objects.create()
        item = PurchaseOrderItem.objects.create(
            purchase_order=purchase_order,
            product=product,
            quantity=2,
            unit_price=Decimal("12.50"),
        )

        item.unit_price = Decimal("18.75")
        item.save()
        product.refresh_from_db()

        self.assertEqual(item.unit_price, Decimal("18.75"))
        self.assertEqual(product.purchase_price, Decimal("12.50"))


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class PurchaseOrderAdminAutosaveTests(TestCase):

    def setUp(self):
        CompanySetting.objects.create(
            company_name="Societe Test",
            vat_amount=Decimal("20.00"),
        )
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password123",
        )
        self.client.force_login(self.user)

    def test_autosave_updates_existing_item_price_without_updating_product_default_price(self):
        product = Product.objects.create(
            description="Produit Prix PO Autosave",
            part_number="PO-AUTO-PRICE",
            hs_code="8504.40",
            purchase_price=Decimal("12.50"),
            sale_price=Decimal("20.00"),
        )
        purchase_order = PurchaseOrder.objects.create(vat_percent=Decimal("20.00"))
        item = PurchaseOrderItem.objects.create(
            purchase_order=purchase_order,
            product=product,
            description=product.description,
            part_number=product.part_number,
            hs_code=product.hs_code,
            quantity=2,
            unit_price=Decimal("12.50"),
        )

        response = self.client.post(
            reverse("admin:purchase_purchaseorder_autosave", args=[purchase_order.pk]),
            {
                "purchase_number": purchase_order.purchase_number,
                "purchase_date": purchase_order.purchase_date.strftime("%Y-%m-%d"),
                "seller": "",
                "requester": "",
                "sent_by": "",
                "shipment": "",
                "freight": "0.00",
                "vat_percent": "20.00",
                "sales_condition": "",
                "payment_condition": "",
                "delivery_terms": "",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "1",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-id": str(item.pk),
                "items-0-purchase_order": str(purchase_order.pk),
                "items-0-product": str(product.pk),
                "items-0-hs_code": product.hs_code,
                "items-0-part_number": product.part_number,
                "items-0-quantity": "2",
                "items-0-unit_price": "18.75",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        item.refresh_from_db()
        product.refresh_from_db()

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(item.unit_price, Decimal("18.75"))
        self.assertEqual(product.purchase_price, Decimal("12.50"))

    def test_autosave_does_not_create_new_inline_items(self):
        product = Product.objects.create(
            description="Produit Nouveau PO Autosave",
            part_number="PO-AUTO-NEW",
            hs_code="8504.40",
            purchase_price=Decimal("12.50"),
            sale_price=Decimal("20.00"),
        )
        purchase_order = PurchaseOrder.objects.create(vat_percent=Decimal("20.00"))

        response = self.client.post(
            reverse("admin:purchase_purchaseorder_autosave", args=[purchase_order.pk]),
            {
                "purchase_number": purchase_order.purchase_number,
                "purchase_date": purchase_order.purchase_date.strftime("%Y-%m-%d"),
                "seller": "",
                "requester": "",
                "sent_by": "",
                "shipment": "",
                "freight": "0.00",
                "vat_percent": "20.00",
                "sales_condition": "",
                "payment_condition": "",
                "delivery_terms": "",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-id": "",
                "items-0-purchase_order": str(purchase_order.pk),
                "items-0-product": str(product.pk),
                "items-0-hs_code": product.hs_code,
                "items-0-part_number": product.part_number,
                "items-0-quantity": "2",
                "items-0-unit_price": "12.50",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(purchase_order.items.count(), 0)

    def test_save_and_add_another_redirects_to_new_purchase_order_form(self):
        purchase_order = PurchaseOrder.objects.create(vat_percent=Decimal("20.00"))

        response = self.client.post(
            reverse("admin:purchase_purchaseorder_change", args=[purchase_order.pk]),
            {
                "purchase_date": purchase_order.purchase_date.strftime("%Y-%m-%d"),
                "seller": "",
                "sent_by": "",
                "shipment": "",
                "freight": "0.00",
                "vat_percent": "20.00",
                "sales_condition": "",
                "payment_condition": "",
                "delivery_terms": "",
                "items-TOTAL_FORMS": "0",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "1000",
                "_addanother": "Save and add another",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("admin:purchase_purchaseorder_add"))
