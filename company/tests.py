import shutil
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

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
