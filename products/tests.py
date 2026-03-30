from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from .admin import ProductAdmin
from .models import Product


class ProductModelTests(TestCase):

    def test_admin_label_prefers_part_number_then_description(self):
        product = Product.objects.create(
            description="Produit A",
            part_number="REF-123",
            unit_qty=8,
            sale_price=Decimal("19.90"),
        )

        self.assertEqual(str(product), "REF-123 - Produit A")

    def test_admin_label_uses_description_when_part_number_is_missing(self):
        product = Product.objects.create(
            description="Produit Sans Reference",
            unit_qty=8,
            sale_price=Decimal("19.90"),
        )

        self.assertEqual(str(product), "Produit Sans Reference")


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
