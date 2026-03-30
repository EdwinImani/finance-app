from decimal import Decimal

from django.test import TestCase

from company.models import CompanySetting
from partners.models import Partner
from products.models import Product

from .models import CommercialInvoice, CommercialInvoiceItem, ProformaInvoice, ProformaInvoiceItem


class ProformaConversionTests(TestCase):

    def setUp(self):
        CompanySetting.objects.create(
            company_name="Societe Test",
            vat_amount=Decimal("20.00"),
        )
        self.importer = Partner.objects.create(
            description="Client Test",
            partner_type="importer",
        )
        self.product = Product.objects.create(
            description="Produit Test",
            unit_qty=10,
            sale_price=Decimal("25.00"),
        )

    def test_convert_to_commercial_decreases_product_quantity(self):
        proforma = ProformaInvoice.objects.create(importer=self.importer)
        ProformaInvoiceItem.objects.create(
            invoice=proforma,
            product=self.product,
            quantity=3,
            unit_price=Decimal("25.00"),
        )

        commercial = proforma.convert_to_commercial()

        self.product.refresh_from_db()

        self.assertIsInstance(commercial, CommercialInvoice)
        self.assertEqual(commercial.items.count(), 1)
        self.assertEqual(self.product.unit_qty, 7)

    def test_convert_to_commercial_only_decreases_stock_once(self):
        proforma = ProformaInvoice.objects.create(importer=self.importer)
        ProformaInvoiceItem.objects.create(
            invoice=proforma,
            product=self.product,
            quantity=4,
            unit_price=Decimal("25.00"),
        )

        first_commercial = proforma.convert_to_commercial()
        second_commercial = proforma.convert_to_commercial()

        self.product.refresh_from_db()

        self.assertEqual(first_commercial.pk, second_commercial.pk)
        self.assertEqual(CommercialInvoice.objects.count(), 1)
        self.assertEqual(self.product.unit_qty, 6)

    def test_convert_to_commercial_keeps_proforma_hs_code(self):
        proforma = ProformaInvoice.objects.create(
            importer=self.importer,
            hs_code="8544.42",
        )
        ProformaInvoiceItem.objects.create(
            invoice=proforma,
            product=self.product,
            quantity=1,
            unit_price=Decimal("25.00"),
        )

        commercial = proforma.convert_to_commercial()

        self.assertEqual(commercial.items.count(), 1)
        self.assertEqual(commercial.items.first().hs_code, "8544.42")

    def test_total_amount_uses_company_setting_vat(self):
        proforma = ProformaInvoice.objects.create(
            importer=self.importer,
            freight=Decimal("10.00"),
            discount=Decimal("5.00"),
            vat_percent=Decimal("20.00"),
        )
        ProformaInvoiceItem.objects.create(
            invoice=proforma,
            product=self.product,
            quantity=2,
            unit_price=Decimal("25.00"),
        )

        self.assertEqual(proforma.subtotal(), Decimal("50.00"))
        self.assertEqual(proforma.vat_amount(), Decimal("10.00"))
        self.assertEqual(proforma.total_amount(), Decimal("65.00"))

    def test_convert_to_commercial_keeps_invoice_vat_percent(self):
        proforma = ProformaInvoice.objects.create(
            importer=self.importer,
            vat_percent=Decimal("7.50"),
        )
        ProformaInvoiceItem.objects.create(
            invoice=proforma,
            product=self.product,
            quantity=2,
            unit_price=Decimal("25.00"),
        )

        commercial = proforma.convert_to_commercial()

        self.assertEqual(commercial.vat_percent, Decimal("7.50"))


class CommercialInvoiceStockTests(TestCase):

    def setUp(self):
        CompanySetting.objects.create(
            company_name="Societe Test",
            vat_amount=Decimal("20.00"),
        )
        self.importer = Partner.objects.create(
            description="Client Stock",
            partner_type="importer",
        )
        self.product = Product.objects.create(
            description="Produit Stock",
            unit_qty=20,
            sale_price=Decimal("15.00"),
        )
        self.other_product = Product.objects.create(
            description="Produit Secondaire",
            unit_qty=12,
            sale_price=Decimal("18.00"),
        )
        self.invoice = CommercialInvoice.objects.create(importer=self.importer)

    def test_create_item_decreases_product_stock(self):
        CommercialInvoiceItem.objects.create(
            invoice=self.invoice,
            product=self.product,
            quantity=4,
            unit_price=Decimal("15.00"),
        )

        self.product.refresh_from_db()

        self.assertEqual(self.product.unit_qty, 16)

    def test_update_item_quantity_updates_product_stock(self):
        item = CommercialInvoiceItem.objects.create(
            invoice=self.invoice,
            product=self.product,
            quantity=4,
            unit_price=Decimal("15.00"),
        )

        item.quantity = 7
        item.save()

        self.product.refresh_from_db()

        self.assertEqual(self.product.unit_qty, 13)

    def test_change_item_product_restores_old_stock_and_decreases_new_one(self):
        item = CommercialInvoiceItem.objects.create(
            invoice=self.invoice,
            product=self.product,
            quantity=5,
            unit_price=Decimal("15.00"),
        )

        item.product = self.other_product
        item.quantity = 3
        item.unit_price = Decimal("18.00")
        item.save()

        self.product.refresh_from_db()
        self.other_product.refresh_from_db()

        self.assertEqual(self.product.unit_qty, 20)
        self.assertEqual(self.other_product.unit_qty, 9)

    def test_delete_item_restores_product_stock(self):
        item = CommercialInvoiceItem.objects.create(
            invoice=self.invoice,
            product=self.product,
            quantity=6,
            unit_price=Decimal("15.00"),
        )

        item.delete()

        self.product.refresh_from_db()

        self.assertEqual(self.product.unit_qty, 20)
