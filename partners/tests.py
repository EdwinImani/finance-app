from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from partners.models import Partner, PartnerAddress, PartnerPhone


class StaffPartnerPermissionTests(TestCase):

    def setUp(self):
        group = Group.objects.create(name="Staff")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="partners", codename="view_partner"
            ),
            Permission.objects.get(
                content_type__app_label="partners", codename="add_partner"
            ),
        )
        self.user = get_user_model().objects.create_user(
            username="partner-staff",
            password="password123",
            is_active=True,
            is_staff=True,
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)

    def test_staff_can_add_but_cannot_change_existing_partner(self):
        partner = Partner.objects.create(
            description="Existing partner",
            partner_type="seller",
        )

        self.assertEqual(
            self.client.get(reverse("admin:partners_partner_add")).status_code,
            200,
        )
        response = self.client.get(
            reverse("admin:partners_partner_change", args=[partner.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="_save"')


class PartnerAdminAutosaveTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password123",
        )
        self.client.force_login(self.user)

    def test_autosave_does_not_create_new_address_or_phone_rows(self):
        partner = Partner.objects.create(
            description="Partner Autosave",
            partner_type="seller",
            email="seller@example.com",
        )

        response = self.client.post(
            reverse("admin:partners_partner_autosave", args=[partner.pk]),
            {
                "description": "Partner Autosave Updated",
                "partner_type": "seller",
                "email": "seller@example.com",
                "fax": "",
                "website": "",
                "addresses-TOTAL_FORMS": "1",
                "addresses-INITIAL_FORMS": "0",
                "addresses-MIN_NUM_FORMS": "0",
                "addresses-MAX_NUM_FORMS": "1000",
                "addresses-0-id": "",
                "addresses-0-partner": str(partner.pk),
                "addresses-0-address": "12 Rue Test",
                "phones-TOTAL_FORMS": "1",
                "phones-INITIAL_FORMS": "0",
                "phones-MIN_NUM_FORMS": "0",
                "phones-MAX_NUM_FORMS": "1000",
                "phones-0-id": "",
                "phones-0-partner": str(partner.pk),
                "phones-0-phone_number": "+33 1 23 45 67 89",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        partner.refresh_from_db()

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(partner.description, "Partner Autosave Updated")
        self.assertEqual(PartnerAddress.objects.filter(partner=partner).count(), 0)
        self.assertEqual(PartnerPhone.objects.filter(partner=partner).count(), 0)

    def test_autosave_updates_existing_address_and_phone_rows(self):
        partner = Partner.objects.create(
            description="Partner Existing",
            partner_type="seller",
            email="seller@example.com",
        )
        address = PartnerAddress.objects.create(partner=partner, address="Old Address")
        phone = PartnerPhone.objects.create(partner=partner, phone_number="+33 1 00 00 00 00")

        response = self.client.post(
            reverse("admin:partners_partner_autosave", args=[partner.pk]),
            {
                "description": "Partner Existing",
                "partner_type": "seller",
                "email": "seller@example.com",
                "fax": "",
                "website": "",
                "addresses-TOTAL_FORMS": "1",
                "addresses-INITIAL_FORMS": "1",
                "addresses-MIN_NUM_FORMS": "0",
                "addresses-MAX_NUM_FORMS": "1000",
                "addresses-0-id": str(address.pk),
                "addresses-0-partner": str(partner.pk),
                "addresses-0-address": "New Address",
                "phones-TOTAL_FORMS": "1",
                "phones-INITIAL_FORMS": "1",
                "phones-MIN_NUM_FORMS": "0",
                "phones-MAX_NUM_FORMS": "1000",
                "phones-0-id": str(phone.pk),
                "phones-0-partner": str(partner.pk),
                "phones-0-phone_number": "+33 1 11 11 11 11",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        address.refresh_from_db()
        phone.refresh_from_db()

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(address.address, "New Address")
        self.assertEqual(phone.phone_number, "+33 1 11 11 11 11")
