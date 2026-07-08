from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.admin.sites import AdminSite
from django.core.management import call_command
from django.test import TestCase

from .admin import ProductAdmin
from .models import Product


class ProductModelTests(TestCase):

    def test_admin_label_uses_description_even_when_part_number_exists(self):
        product = Product.objects.create(
            description="Produit A",
            part_number="REF-123",
            unit_qty=8,
            sale_price=Decimal("19.90"),
        )

        self.assertEqual(str(product), "Produit A")

    def test_admin_label_uses_description_when_part_number_is_missing(self):
        product = Product.objects.create(
            description="Produit Sans Reference",
            unit_qty=8,
            sale_price=Decimal("19.90"),
        )

        self.assertEqual(str(product), "Produit Sans Reference")

    def test_description_can_be_used_by_multiple_products(self):
        Product.objects.create(description="JOINT", part_number="K-39228")
        Product.objects.create(description="JOINT", part_number="K-40785")

        self.assertEqual(Product.objects.filter(description="JOINT").count(), 2)


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


class ProductCsvImportTests(TestCase):

    def test_import_creates_one_product_per_csv_row_and_generates_unique_part_numbers(self):
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
        self.assertEqual(imported[0].part_number, "PART-DUP-0001")
        self.assertEqual(imported[1].part_number, "K-40785")
        self.assertEqual(imported[2].part_number, "LEGACY-0001")
        self.assertEqual(imported[3].part_number, "PART-DUP-0002")
        self.assertEqual(imported[0].purchase_price, Decimal("2.50"))
        self.assertEqual(imported[1].sale_price, Decimal("5.00"))
        self.assertEqual(imported[2].unit_qty, 7)
