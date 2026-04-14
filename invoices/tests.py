from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from company.models import CompanySetting
from partners.models import Partner
from products.models import Product

from .forms import CommercialInvoiceForm, ProformaInvoiceForm
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
            hs_code="8544.42",
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

    def test_convert_to_commercial_keeps_item_hs_code(self):
        proforma = ProformaInvoice.objects.create(importer=self.importer)
        ProformaInvoiceItem.objects.create(
            invoice=proforma,
            product=self.product,
            hs_code="8544.42",
            quantity=1,
            unit_price=Decimal("25.00"),
        )

        commercial = proforma.convert_to_commercial()

        self.assertEqual(commercial.items.count(), 1)
        self.assertEqual(commercial.items.first().hs_code, "8544.42")

    def test_proforma_item_uses_product_hs_code_by_default(self):
        proforma = ProformaInvoice.objects.create(importer=self.importer)

        item = ProformaInvoiceItem.objects.create(
            invoice=proforma,
            product=self.product,
            quantity=1,
            unit_price=Decimal("25.00"),
        )

        self.assertEqual(item.hs_code, "8544.42")

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


class InvoiceFormVatDefaultTests(TestCase):

    def test_proforma_form_uses_company_vat_as_initial_value(self):
        CompanySetting.objects.create(
            company_name="Societe TVA",
            vat_amount=Decimal("19.60"),
        )

        form = ProformaInvoiceForm()

        self.assertEqual(form.fields["vat_percent"].initial, Decimal("19.60"))

    def test_commercial_form_uses_company_vat_as_initial_value(self):
        CompanySetting.objects.create(
            company_name="Societe TVA",
            vat_amount=Decimal("8.50"),
        )

        form = CommercialInvoiceForm()

        self.assertEqual(form.fields["vat_percent"].initial, Decimal("8.50"))


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
            hs_code="9027.80",
            unit_qty=20,
            sale_price=Decimal("15.00"),
        )
        self.other_product = Product.objects.create(
            description="Produit Secondaire",
            hs_code="8414.59",
            unit_qty=12,
            sale_price=Decimal("18.00"),
        )
        self.invoice = CommercialInvoice.objects.create(importer=self.importer)

    def test_create_item_decreases_product_stock(self):
        item = CommercialInvoiceItem.objects.create(
            invoice=self.invoice,
            product=self.product,
            quantity=4,
            unit_price=Decimal("15.00"),
        )

        self.product.refresh_from_db()

        self.assertEqual(self.product.unit_qty, 16)
        self.assertEqual(item.hs_code, "9027.80")

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


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class CommercialInvoiceAdminDraftTests(TestCase):

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

    def test_add_view_creates_empty_commercial_invoice_draft(self):
        response = self.client.get(reverse("admin:invoices_commercialinvoice_add"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(CommercialInvoice.objects.count(), 1)

        invoice = CommercialInvoice.objects.get()

        self.assertRedirects(
            response,
            reverse("admin:invoices_commercialinvoice_change", args=[invoice.pk]),
        )
        self.assertIsNotNone(invoice.invoice_date)
        self.assertEqual(invoice.vat_percent, Decimal("20.00"))

    def test_draft_add_url_creates_empty_commercial_invoice_draft(self):
        response = self.client.get(reverse("admin:invoices_commercialinvoice_draft_add"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(CommercialInvoice.objects.count(), 1)

        invoice = CommercialInvoice.objects.get()

        self.assertRedirects(
            response,
            reverse("admin:invoices_commercialinvoice_change", args=[invoice.pk]),
        )

    def test_changelist_uses_draft_add_url_for_commercial_invoice_button(self):
        response = self.client.get(reverse("admin:invoices_commercialinvoice_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("admin:invoices_commercialinvoice_draft_add"),
        )

    def test_autosave_does_not_create_inline_items(self):
        importer = Partner.objects.create(
            description="Client Autosave",
            partner_type="importer",
        )
        product = Product.objects.create(
            description="Produit Autosave",
            part_number="AUTO-001",
            hs_code="8403.21",
            unit_qty=20,
            sale_price=Decimal("58.00"),
            purchase_price=Decimal("30.00"),
        )
        invoice = CommercialInvoice.objects.create(importer=importer, vat_percent=Decimal("20.00"))

        response = self.client.post(
            reverse("admin:invoices_commercialinvoice_autosave", args=[invoice.pk]),
            {
                "invoice_date": invoice.invoice_date.strftime("%d/%m/%Y"),
                "importer": str(importer.pk),
                "end_user": "",
                "our_order_no": "",
                "our_reference": "",
                "freight": "0.00",
                "discount": "0.00",
                "vat_percent": "20.00",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-id": "",
                "items-0-invoice": str(invoice.pk),
                "items-0-product": str(product.pk),
                "items-0-hs_code": product.hs_code,
                "items-0-quantity": "5",
                "items-0-unit_price": "58.00",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertIn(response.status_code, {200, 400})
        self.assertEqual(invoice.items.count(), 0)
