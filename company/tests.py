import shutil
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CompanySetting


TEMP_MEDIA_ROOT = Path(__file__).resolve().parents[1] / "test_media"


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CompanySettingLogoTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        TEMP_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_old_logo_file_is_deleted_when_logo_is_replaced(self):
        first_logo = SimpleUploadedFile(
            "logo1.png",
            b"first-logo-content",
            content_type="image/png",
        )
        second_logo = SimpleUploadedFile(
            "logo2.png",
            b"second-logo-content",
            content_type="image/png",
        )

        company = CompanySetting.objects.create(
            company_name="Test Company",
            company_logo=first_logo,
        )

        old_logo_path = Path(company.company_logo.path)

        company.company_logo = second_logo
        company.save()

        self.assertFalse(old_logo_path.exists())
        self.assertTrue(Path(company.company_logo.path).exists())


class CompanySettingAdminTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password123",
        )
        self.client.force_login(self.user)

    def test_save_redirects_to_admin_welcome_page(self):
        company = CompanySetting.objects.create(
            company_name="Test Company",
            year=2026,
        )

        response = self.client.post(
            reverse("admin:company_companysetting_change", args=[company.pk]),
            {
                "year": "2026",
                "company_name": "Updated Company",
                "president": "",
                "company_email": "",
                "company_phone": "",
                "company_fax": "",
                "company_address": "",
                "address": "",
                "siren": "",
                "vat_number": "",
                "bank": "",
                "iban": "",
                "bic": "",
                "currency": "EUR",
                "vat_amount": "20.00",
                "delivery_time": "",
                "terms_conditions": "",
                "proforma_validity": "7",
                "note": "",
                "footer_order": "",
                "footer_invoice": "",
                "invoice_note": "",
                "_save": "Save",
            },
        )

        company.refresh_from_db()
        self.assertEqual(company.company_name, "Updated Company")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/")
