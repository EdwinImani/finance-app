from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from invoices.models import CommercialInvoice, CommercialInvoiceItem, ProformaInvoice
from purchase.models import PurchaseOrder, PurchaseOrderItem
from .admin import ProductAdmin
from .models import Product


class ProductModelTests(TestCase):

    def test_admin_label_includes_part_number_when_it_exists(self):
        product = Product.objects.create(
            description="Produit A",
            part_number="REF-123",
            unit_qty=8,
            sale_price=Decimal("19.90"),
        )

        self.assertEqual(str(product), f"#{product.pk} - Produit A - REF-123")

    def test_admin_label_uses_product_id_when_part_number_is_missing(self):
        product = Product.objects.create(
            description="Produit Sans Reference",
            unit_qty=8,
            sale_price=Decimal("19.90"),
        )

        self.assertEqual(str(product), f"#{product.pk} - Produit Sans Reference")

    def test_description_can_be_used_by_multiple_products(self):
        Product.objects.create(description="JOINT", part_number="K-39228")
        Product.objects.create(description="JOINT", part_number="K-40785")

        self.assertEqual(Product.objects.filter(description="JOINT").count(), 2)

    def test_part_number_can_be_used_by_multiple_products(self):
        Product.objects.create(description="Joint 10mm", part_number="K-39228")
        Product.objects.create(description="Joint 20mm", part_number="K-39228")

        self.assertEqual(Product.objects.filter(part_number="K-39228").count(), 2)


class StaffProductPermissionTests(TestCase):

    def setUp(self):
        group = Group.objects.create(name="Staff")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="products", codename="view_product"
            ),
            Permission.objects.get(
                content_type__app_label="products", codename="add_product"
            ),
        )
        self.user = get_user_model().objects.create_user(
            username="product-staff",
            password="password123",
            is_active=True,
            is_staff=True,
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)

    def test_staff_can_add_but_cannot_change_existing_product(self):
        product = Product.objects.create(description="Existing product")

        self.assertEqual(
            self.client.get(reverse("admin:products_product_add")).status_code,
            200,
        )
        response = self.client.get(
            reverse("admin:products_product_change", args=[product.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="_save"')


class ProductAdminSearchTests(TestCase):

    def setUp(self):
        self.admin = ProductAdmin(Product, AdminSite())
        Product.objects.create(
            description="Shielded Signal Cable 100m",
            part_number="CAB-100",
            note="industrial cable",
        )
        Product.objects.create(
            description="Power Adapter",
            part_number="PWR-50",
            note="adapter",
        )

    def test_search_finds_product_by_exact_part_number(self):
        queryset = Product.objects.all()

        results, _ = self.admin.get_search_results(None, queryset, "CAB-100")

        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().description, "Shielded Signal Cable 100m")

    def test_search_finds_product_by_description_words(self):
        queryset = Product.objects.all()

        results, _ = self.admin.get_search_results(None, queryset, "Signal 100m")

        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().part_number, "CAB-100")

    def test_product_admin_form_hides_unit_price(self):
        form_class = self.admin.get_form(None)

        self.assertNotIn("unit_price", form_class.base_fields)
        self.assertIn("sale_price", form_class.base_fields)
        self.assertIn("purchase_price", form_class.base_fields)


class ProductAdminReturnTests(TestCase):

    def setUp(self):
        self.admin = ProductAdmin(Product, AdminSite())
        self.factory = RequestFactory()

    def _request(self, return_field, return_item_id=""):
        data = {
            "_return_to": "/admin/invoices/proformainvoice/1/change/",
            "_return_field": return_field,
        }
        if return_item_id:
            data["_return_item_id"] = return_item_id
        request = self.factory.post("/admin/products/product/1/change/", data)
        request.get_host = lambda: "127.0.0.1:8000"
        request.is_secure = lambda: False
        return request

    def _add_request(self, return_to, return_field):
        request = self.factory.post(
            "/admin/products/product/add/",
            {
                "_return_to": return_to,
                "_return_field": return_field,
                "_return_product_action": "add",
            },
        )
        request.get_host = lambda: "127.0.0.1:8000"
        request.is_secure = lambda: False
        return request

    def test_save_redirects_to_admin_return_url(self):
        product = Product.objects.create(description="Return Save Product")
        request = self.factory.post(
            "/admin/products/product/1/change/",
            {"admin_return_url": "/admin/products/product/"},
        )
        request.get_host = lambda: "127.0.0.1:8000"
        request.is_secure = lambda: False

        response = self.admin.response_change(request, product)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/products/product/")

    def test_get_return_url_uses_admin_return_url_query(self):
        request = self.factory.get(
            "/admin/products/product/1/change/",
            {"admin_return_url": "/admin/products/product/?p=2"},
        )
        request.get_host = lambda: "127.0.0.1:8000"
        request.is_secure = lambda: False

        self.assertEqual(
            self.admin._get_return_url(request),
            "/admin/products/product/?p=2",
        )

    def test_save_without_return_url_falls_back_to_model_list(self):
        product = Product.objects.create(description="Fallback Save Product")
        request = self.factory.post("/admin/products/product/1/change/", {})
        request.get_host = lambda: "127.0.0.1:8000"
        request.is_secure = lambda: False

        response = self.admin.response_change(request, product)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/products/product/")

    def test_return_from_product_creates_proforma_item(self):
        product = Product.objects.create(
            description="Returned Invoice Product",
            part_number="RET-INV",
            hs_code="8504.40",
            sale_price=Decimal("12.30"),
        )
        invoice = ProformaInvoice.objects.create()
        request = self._request("items-0-product")

        self.admin._attach_product_to_return_item(
            request,
            product,
            f"/admin/invoices/proformainvoice/{invoice.pk}/change/",
        )

        item = invoice.items.get()
        self.assertEqual(item.product, product)
        self.assertEqual(item.part_number, "RET-INV")
        self.assertEqual(item.hs_code, "8504.40")
        self.assertEqual(item.unit_price, Decimal("12.30"))

    def test_add_product_save_returns_to_proforma_without_creating_duplicate_item(self):
        product = Product.objects.create(
            description="New Product From Invoice",
            part_number="NEW-INV",
            hs_code="8504.40",
            sale_price=Decimal("16.90"),
        )
        invoice = ProformaInvoice.objects.create()
        return_to = f"/admin/invoices/proformainvoice/{invoice.pk}/change/"
        request = self._add_request(return_to, "items-0-product")

        response = self.admin.response_add(request, product)

        self.assertEqual(response.status_code, 302)
        self.assertIn(return_to, response["Location"])
        self.assertIn("_selected_product_field=items-0-product", response["Location"])
        self.assertIn(f"_selected_product_id={product.pk}", response["Location"])
        self.assertFalse(invoice.items.exists())

    def test_empty_add_product_from_document_returns_without_creating_product(self):
        return_to = "/admin/invoices/proformainvoice/1/change/"
        request = self._add_request(return_to, "items-0-product")

        response = self.admin.changeform_view(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], return_to)
        self.assertFalse(Product.objects.exists())

    def test_started_add_product_from_document_still_requires_description(self):
        request = self._add_request("/admin/invoices/proformainvoice/1/change/", "items-0-product")
        request.POST = request.POST.copy()
        request.POST["part_number"] = "REF-WITHOUT-DESCRIPTION"

        self.assertFalse(self.admin._is_empty_return_product_add(request))

    def test_return_from_product_creates_purchase_order_item(self):
        product = Product.objects.create(
            description="Returned Purchase Product",
            part_number="RET-PO",
            hs_code="8471.30",
            purchase_price=Decimal("7.80"),
        )
        purchase_order = PurchaseOrder.objects.create()
        request = self._request("items-0-product")

        self.admin._attach_product_to_return_item(
            request,
            product,
            f"/admin/purchase/purchaseorder/{purchase_order.pk}/change/",
        )

        item = purchase_order.items.get()
        self.assertEqual(item.product, product)
        self.assertEqual(item.description, "Returned Purchase Product")
        self.assertEqual(item.part_number, "RET-PO")
        self.assertEqual(item.hs_code, "8471.30")
        self.assertEqual(item.unit_price, Decimal("7.80"))

    def test_edit_product_keeps_custom_commercial_invoice_hs_code(self):
        product = Product.objects.create(
            description="Product Without Default HS",
            part_number="CUSTOM-HS-001",
            hs_code="",
            sale_price=Decimal("12.30"),
        )
        invoice = CommercialInvoice.objects.create(
            price_for="Special customer price",
            freight=Decimal("35.00"),
            terms_conditions="Keep these invoice conditions",
        )
        item = CommercialInvoiceItem.objects.create(
            invoice=invoice,
            product=product,
            hs_code="CUSTOM-8481.80",
            quantity=1,
            unit_price=Decimal("12.30"),
        )
        request = self.factory.post(
            f"/admin/products/product/{product.pk}/change/",
            {
                "_return_to": f"/admin/invoices/commercialinvoice/{invoice.pk}/change/",
                "_return_field": "items-0-product",
                "_return_item_id": str(item.pk),
                "_return_product_action": "edit",
            },
        )
        request.get_host = lambda: "127.0.0.1:8000"
        request.is_secure = lambda: False
        product.part_number = "UPDATED-CUSTOM-HS-001"
        product.sale_price = Decimal("19.40")
        product.save()

        self.admin._update_existing_return_item(
            request,
            product,
            f"/admin/invoices/commercialinvoice/{invoice.pk}/change/",
        )

        item.refresh_from_db()
        invoice.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(item.hs_code, "CUSTOM-8481.80")
        self.assertEqual(item.part_number, "UPDATED-CUSTOM-HS-001")
        self.assertEqual(item.unit_price, Decimal("19.40"))
        self.assertEqual(product.hs_code, "")
        self.assertEqual(invoice.price_for, "Special customer price")
        self.assertEqual(invoice.freight, Decimal("35.00"))
        self.assertEqual(invoice.terms_conditions, "Keep these invoice conditions")

    def test_edit_product_keeps_custom_purchase_order_hs_code(self):
        product = Product.objects.create(
            description="Purchase Product Without Default HS",
            part_number="PO-CUSTOM-HS-001",
            hs_code="",
            purchase_price=Decimal("7.80"),
        )
        purchase_order = PurchaseOrder.objects.create(
            freight=Decimal("42.00"),
            sales_condition="Keep these sales conditions",
            shipment="Keep this shipment",
        )
        item = PurchaseOrderItem.objects.create(
            purchase_order=purchase_order,
            product=product,
            hs_code="CUSTOM-8504.40",
            quantity=1,
            unit_price=Decimal("7.80"),
        )
        return_to = (
            f"/admin/purchase/purchaseorder/{purchase_order.pk}/change/"
        )
        request = self.factory.post(
            f"/admin/products/product/{product.pk}/change/",
            {
                "_return_to": return_to,
                "_return_field": "items-0-product",
                "_return_item_id": str(item.pk),
                "_return_product_action": "edit",
            },
        )
        request.get_host = lambda: "127.0.0.1:8000"
        request.is_secure = lambda: False
        product.description = "Updated Purchase Product"
        product.part_number = "UPDATED-PO-HS-001"
        product.purchase_price = Decimal("9.25")
        product.save()

        self.admin._update_existing_return_item(
            request,
            product,
            return_to,
        )

        item.refresh_from_db()
        purchase_order.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(item.hs_code, "CUSTOM-8504.40")
        self.assertEqual(item.description, "Updated Purchase Product")
        self.assertEqual(item.part_number, "UPDATED-PO-HS-001")
        self.assertEqual(item.unit_price, Decimal("9.25"))
        self.assertEqual(product.hs_code, "")
        self.assertEqual(purchase_order.freight, Decimal("42.00"))
        self.assertEqual(purchase_order.sales_condition, "Keep these sales conditions")
        self.assertEqual(purchase_order.shipment, "Keep this shipment")


class ProductCsvImportTests(TestCase):

    def test_import_creates_one_product_per_csv_row_and_keeps_duplicate_part_numbers(self):
        Product.objects.create(description="Existing", part_number="DUP-001")

        content = "\n".join(
            [
                "sep=;",
                "product_name;part_number;unit_price;purchase_price;sale_price;quantity;note",
                "JOINT;DUP-001;1;2.50;4.00;3;First duplicate",
                "JOINT;K-40785;1;3.00;5.00;6;Second joint",
                "JOINT;;1;4.00;6.00;7;Missing reference",
                "GASKET;DUP-001;1;1.25;2.50;2;Second duplicate",
            ]
        )

        with TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "products.csv"
            csv_path.write_text(content, encoding="utf-8")

            call_command("import_products_csv", str(csv_path))

        imported = Product.objects.exclude(description="Existing").order_by("id")

        self.assertEqual(imported.count(), 4)
        self.assertEqual(Product.objects.filter(description="JOINT").count(), 3)
        self.assertEqual(imported[0].part_number, "DUP-001")
        self.assertEqual(imported[1].part_number, "K-40785")
        self.assertEqual(imported[2].part_number, "LEGACY-0001")
        self.assertEqual(imported[3].part_number, "DUP-001")
        self.assertEqual(imported[0].purchase_price, Decimal("2.50"))
        self.assertEqual(imported[1].sale_price, Decimal("5.00"))
        self.assertEqual(imported[2].unit_qty, 7)
