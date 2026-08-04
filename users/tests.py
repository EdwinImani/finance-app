from django.contrib import admin
from django.contrib.auth import authenticate
from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.contrib.staticfiles import finders
from django.template.loader import get_template
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from company.models import CompanySetting
from invoices.models import CommercialInvoice
from partners.models import Partner
from products.models import Product
from purchase.models import PurchaseOrder
from users.forms import AdminUserChangeForm, AdminUserCreationForm


class PasswordToggleTests(SimpleTestCase):

    def test_login_and_admin_pages_load_accessible_password_toggle(self):
        base_template = get_template("admin/base_site.html").template.source
        login_template = get_template("admin/login.html").template.source
        with open(finders.find("admin/js/password_toggle.js"), encoding="utf-8") as script_file:
            script = script_file.read()

        self.assertIn("admin/js/password_toggle.js", base_template)
        self.assertIn('button.type = "button"', script)
        self.assertIn('input.type = show ? "text" : "password"', script)
        self.assertIn("data-password-toggle", script)
        self.assertIn("Afficher le mot de passe", script)
        self.assertNotIn("console.log", script)
        self.assertIn(".password-field-wrapper", login_template)
        self.assertIn("width: 100% !important", login_template)
        self.assertIn("height: 44px !important", login_template)
        self.assertIn("padding: 0 48px 0 16px !important", login_template)
        self.assertIn("position: absolute !important", login_template)


class UserPasswordAuthenticationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.staff_group = Group.objects.create(name="Staff")
        cls.manager_group = Group.objects.create(name="Manager")

    def creation_form_data(self, **overrides):
        data = {
            "username": "created-staff",
            "first_name": "Created",
            "last_name": "User",
            "email": "created@example.com",
            "password1": "Secure-Test-Password-482!",
            "password2": "Secure-Test-Password-482!",
            "is_active": True,
            "is_staff": False,
            "groups": [self.staff_group.pk],
        }
        data.update(overrides)
        return data

    def test_admin_creation_form_hashes_password_and_authenticates_staff_role(self):
        raw_password = "Secure-Test-Password-482!"
        form = AdminUserCreationForm(data=self.creation_form_data())

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertNotEqual(user.password, raw_password)
        self.assertTrue(user.check_password(raw_password))
        self.assertTrue(user.has_usable_password())
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(authenticate(username=user.username, password=raw_password), user)
        self.assertIsNone(authenticate(username=user.username, password="wrong-password"))

    def test_django_admin_add_view_creates_login_capable_user(self):
        administrator = User.objects.create_superuser(
            username="user-creator",
            email="creator@example.com",
            password="Creator-Test-Password-729!",
        )
        self.client.force_login(administrator)

        response = self.client.post(
            reverse("admin:auth_user_add"),
            self.creation_form_data(username="admin-created-user"),
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="admin-created-user")
        self.assertTrue(user.check_password("Secure-Test-Password-482!"))
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

        self.client.logout()
        login_response = self.client.post(
            reverse("admin:login"),
            {
                "username": user.username,
                "password": "Secure-Test-Password-482!",
                "next": reverse("admin:index"),
            },
        )
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response["Location"], reverse("admin:index"))

    def test_admin_add_view_saves_global_document_access_checkbox(self):
        administrator = User.objects.create_superuser(
            username="document-permission-admin",
            email="documents-admin@example.com",
            password="Creator-Test-Password-729!",
        )
        self.client.force_login(administrator)

        response = self.client.post(
            reverse("admin:auth_user_add"),
            self.creation_form_data(
                username="global-document-user",
                can_view_all_documents="on",
            ),
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="global-document-user")
        self.assertTrue(user.has_perm("invoices.view_all_documents"))

    def test_admin_change_view_enables_access_to_unowned_documents(self):
        administrator = User.objects.create_superuser(
            username="existing-user-admin",
            email="existing-admin@example.com",
            password="Creator-Test-Password-729!",
        )
        user = User.objects.create_user(
            username="existing-scoped-user",
            password="Secure-Test-Password-482!",
            is_active=True,
            is_staff=True,
        )
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="invoices",
                codename="view_commercialinvoice",
            )
        )
        unowned_invoice = CommercialInvoice.objects.create()
        self.client.force_login(administrator)

        response = self.client.post(
            reverse("admin:auth_user_change", args=[user.pk]),
            {
                "username": user.username,
                "password": user.password,
                "first_name": "",
                "last_name": "",
                "email": "",
                "is_active": "on",
                "is_staff": "on",
                "can_view_all_documents": "on",
                "groups": [],
                "user_permissions": [
                    Permission.objects.get(
                        content_type__app_label="invoices",
                        codename="view_commercialinvoice",
                    ).pk
                ],
            },
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(pk=user.pk)
        self.assertTrue(user.has_perm("invoices.view_all_documents"))

        self.client.force_login(user)
        response = self.client.get(
            reverse("admin:invoices_commercialinvoice_changelist")
        )
        self.assertContains(response, unowned_invoice.invoice_number)

    def test_manager_role_is_created_as_staff_without_superuser_access(self):
        form = AdminUserCreationForm(
            data=self.creation_form_data(
                username="created-manager",
                groups=[self.manager_group.pk],
            )
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

        self.client.logout()
        response = self.client.post(
            reverse("admin:login"),
            {
                "username": user.username,
                "password": "Secure-Test-Password-482!",
                "next": reverse("admin:index"),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("admin:index"))

    def test_creation_form_rejects_mismatched_passwords(self):
        form = AdminUserCreationForm(
            data=self.creation_form_data(password2="Different-Test-Password-937!")
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_inactive_user_cannot_authenticate(self):
        user = User.objects.create_user(
            username="inactive-user",
            password="Secure-Test-Password-482!",
            is_active=False,
            is_staff=True,
        )

        self.assertIsNone(
            authenticate(username=user.username, password="Secure-Test-Password-482!")
        )

    def test_non_staff_user_cannot_enter_admin(self):
        user = User.objects.create_user(
            username="site-only-user",
            password="Secure-Test-Password-482!",
            is_active=True,
            is_staff=False,
        )

        self.client.force_login(user)
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response["Location"])

    def test_superuser_keeps_admin_access(self):
        user = User.objects.create_superuser(
            username="security-superuser",
            email="security@example.com",
            password="Secure-Test-Password-482!",
        )

        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)


class UserAdminConfigurationTests(TestCase):

    def setUp(self):
        self.user_admin = admin.site._registry[User]
        self.group_admin = admin.site._registry[Group]

    def test_user_admin_list_search_filters_and_horizontal_fields_are_configured(self):
        self.assertEqual(
            self.user_admin.list_display,
            (
                "username",
                "email",
                "first_name",
                "last_name",
                "is_staff",
                "is_superuser",
                "is_active",
                "last_login",
            ),
        )
        self.assertEqual(
            self.user_admin.search_fields,
            (
                "username",
                "email",
                "first_name",
                "last_name",
            ),
        )
        self.assertEqual(
            self.user_admin.list_filter,
            (
                "is_staff",
                "is_superuser",
                "is_active",
                "groups",
            ),
        )
        self.assertEqual(
            self.user_admin.filter_horizontal,
            (
                "groups",
                "user_permissions",
            ),
        )

    def test_user_admin_detail_sections_and_readonly_fields_are_configured(self):
        self.assertEqual(
            [section[0] for section in self.user_admin.fieldsets],
            [
                "Informations principales",
                "Permissions et groupes",
                "Dates importantes",
            ],
        )
        self.assertEqual(
            self.user_admin.readonly_fields,
            (
                "last_login",
                "date_joined",
            ),
        )

    def test_group_admin_list_search_sections_and_horizontal_fields_are_configured(self):
        self.assertEqual(
            self.group_admin.list_display,
            (
                "name",
                "permissions_count",
            ),
        )
        self.assertEqual(self.group_admin.search_fields, ("name",))
        self.assertEqual(
            [section[0] for section in self.group_admin.fieldsets],
            [
                "Nom du groupe",
                "Permissions",
            ],
        )
        self.assertEqual(self.group_admin.filter_horizontal, ("permissions",))

    def test_group_permissions_count_uses_existing_permissions(self):
        group = Group.objects.create(name="Managers")
        permissions = list(self.group_admin.model._meta.default_permissions)

        self.assertEqual(permissions, ["add", "change", "delete", "view"])
        self.assertEqual(self.group_admin.permissions_count(group), 0)

    def test_user_form_exposes_and_saves_global_document_access_checkbox(self):
        user = User.objects.create_user("document-access-user", password="test-password")
        permission = Permission.objects.get(
            content_type__app_label="invoices",
            codename="view_all_documents",
        )
        form = AdminUserChangeForm(instance=user)

        self.assertIn("can_view_all_documents", form.fields)
        self.assertEqual(
            form.fields["can_view_all_documents"].label,
            "Can view all users' invoices and purchase orders",
        )

        form.cleaned_data = {"can_view_all_documents": True}
        form._sync_document_access_permission()
        self.assertTrue(user.user_permissions.filter(pk=permission.pk).exists())

        form.cleaned_data = {"can_view_all_documents": False}
        form._sync_document_access_permission()
        self.assertFalse(user.user_permissions.filter(pk=permission.pk).exists())

    def test_user_group_and_permission_help_layout_has_full_width_overrides(self):
        template_source = get_template("admin/base_site.html").template.source

        self.assertIn(
            "body.app-auth.model-user .form-row.field-groups .help",
            template_source,
        )
        self.assertIn(
            "body.app-auth.model-user .form-row.field-user_permissions .help",
            template_source,
        )
        self.assertIn("width: min(1200px, 100%) !important", template_source)
        self.assertIn("word-break: normal !important", template_source)


class RoleAccessControlTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.administrator_group = Group.objects.create(name="Administrator")
        cls.manager_group = Group.objects.create(name="Manager")
        cls.staff_group = Group.objects.create(name="Staff")

        cls.administrator = User.objects.create_user(
            "administrator", password="test-password", is_staff=True
        )
        cls.administrator.groups.add(cls.administrator_group)

        cls.manager = User.objects.create_user(
            "manager", password="test-password", is_staff=True
        )
        cls.manager.groups.add(cls.manager_group)

        cls.staff_user = User.objects.create_user(
            "staff-user", password="test-password", is_staff=True
        )
        cls.staff_user.groups.add(cls.staff_group)

        cls.other_staff = User.objects.create_user(
            "other-staff", password="test-password", is_staff=True
        )
        cls.other_staff.groups.add(cls.staff_group)

        # Give broad native permissions deliberately. Role rules must only remove access.
        all_permissions = Permission.objects.all()
        scoped_staff_permissions = all_permissions.exclude(
            content_type__app_label="invoices",
            codename="view_all_documents",
        )
        cls.administrator.user_permissions.set(all_permissions)
        cls.manager.user_permissions.set(all_permissions)
        cls.staff_user.user_permissions.set(scoped_staff_permissions)
        cls.other_staff.user_permissions.set(scoped_staff_permissions)

        cls.product = Product.objects.create(description="Test product")
        cls.partner = Partner.objects.create(
            description="Test importer", partner_type="importer"
        )
        cls.company = CompanySetting.objects.create(company_name="Test company")

        cls.own_invoice = CommercialInvoice.objects.create(created_by=cls.staff_user)
        cls.other_invoice = CommercialInvoice.objects.create(created_by=cls.other_staff)
        cls.old_invoice = CommercialInvoice.objects.create(created_by=cls.staff_user)
        cls.unowned_invoice = CommercialInvoice.objects.create()
        CommercialInvoice.objects.filter(pk=cls.old_invoice.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        cls.own_purchase = PurchaseOrder.objects.create(created_by=cls.staff_user)
        cls.other_purchase = PurchaseOrder.objects.create(created_by=cls.other_staff)
        cls.old_purchase = PurchaseOrder.objects.create(created_by=cls.staff_user)
        cls.unowned_purchase = PurchaseOrder.objects.create()
        PurchaseOrder.objects.filter(pk=cls.old_purchase.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

    def login(self, user):
        self.client.force_login(user)

    def test_only_administrator_role_can_open_users_and_groups(self):
        for user in (self.manager, self.staff_user):
            self.login(user)
            self.assertEqual(self.client.get(reverse("admin:auth_user_changelist")).status_code, 403)
            self.assertEqual(self.client.get(reverse("admin:auth_group_changelist")).status_code, 403)

        self.login(self.administrator)
        self.assertEqual(self.client.get(reverse("admin:auth_user_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:auth_group_changelist")).status_code, 200)

    def test_superuser_gets_200_on_all_user_admin_pages_and_can_delete(self):
        superuser = User.objects.create_superuser(
            "root-admin", password="test-password", email="root@example.com"
        )
        target = User.objects.create_user("user-to-delete", password="test-password")
        self.client.force_login(superuser)

        delete_url = reverse("admin:auth_user_delete", args=[target.pk])
        self.assertEqual(
            self.client.get(reverse("admin:auth_user_changelist")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("admin:auth_user_add")).status_code,
            200,
        )
        change_response = self.client.get(
            reverse("admin:auth_user_change", args=[target.pk])
        )
        self.assertEqual(change_response.status_code, 200)
        self.assertContains(change_response, delete_url)
        delete_response = self.client.get(delete_url)
        self.assertEqual(delete_response.status_code, 200)
        self.assertContains(delete_response, "Yes, I’m sure")
        self.assertEqual(
            self.client.get(reverse("admin:auth_group_changelist")).status_code,
            200,
        )
        response = self.client.post(delete_url, {"post": "yes"})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=target.pk).exists())
        self.assertEqual(
            self.client.get(reverse("admin:auth_user_changelist")).status_code,
            200,
        )

    def test_group_form_keeps_django_filtered_permissions_widget(self):
        self.login(self.administrator)
        response = self.client.get(reverse("admin:auth_group_add"))
        self.assertEqual(response.status_code, 200)
        # Django 6 creates the two boxes in JavaScript from this native widget.
        self.assertContains(response, 'id="id_permissions"')
        self.assertContains(response, 'class="selectfilter"')
        self.assertContains(response, 'data-field-name="permissions"')

    def test_manager_and_staff_keep_their_own_password_change_page(self):
        for user in (self.manager, self.staff_user):
            self.login(user)
            self.assertEqual(self.client.get(reverse("admin:password_change")).status_code, 200)

    def test_staff_can_add_products_and_partners_but_existing_records_are_read_only(self):
        self.login(self.staff_user)
        self.assertEqual(self.client.get(reverse("admin:products_product_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:partners_partner_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:products_product_add")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:partners_partner_add")).status_code, 200)
        product_response = self.client.get(
            reverse("admin:products_product_change", args=[self.product.pk])
        )
        partner_response = self.client.get(
            reverse("admin:partners_partner_change", args=[self.partner.pk])
        )
        self.assertNotContains(product_response, 'name="_save"')
        self.assertNotContains(partner_response, 'name="_save"')
        self.assertEqual(
            self.client.get(reverse("admin:products_product_delete", args=[self.product.pk])).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse("admin:partners_partner_delete", args=[self.partner.pk])).status_code,
            403,
        )

    def test_staff_sees_all_own_documents_regardless_of_creation_date(self):
        self.login(self.staff_user)
        invoice_response = self.client.get(reverse("admin:invoices_commercialinvoice_changelist"))
        self.assertContains(invoice_response, self.own_invoice.invoice_number)
        self.assertNotContains(invoice_response, self.other_invoice.invoice_number)
        self.assertContains(invoice_response, self.old_invoice.invoice_number)
        self.assertNotContains(invoice_response, self.unowned_invoice.invoice_number)

        purchase_response = self.client.get(reverse("admin:purchase_purchaseorder_changelist"))
        self.assertContains(purchase_response, self.own_purchase.purchase_number)
        self.assertNotContains(purchase_response, self.other_purchase.purchase_number)
        self.assertContains(purchase_response, self.old_purchase.purchase_number)
        self.assertNotContains(purchase_response, self.unowned_purchase.purchase_number)

        invoice_search = self.client.get(
            reverse("admin:invoices_commercialinvoice_changelist"),
            {"q": self.other_invoice.invoice_number},
        )
        purchase_search = self.client.get(
            reverse("admin:purchase_purchaseorder_changelist"),
            {"q": self.other_purchase.purchase_number},
        )
        self.assertNotIn(
            self.other_invoice.pk,
            invoice_search.context["cl"].result_list.values_list("pk", flat=True),
        )
        self.assertNotIn(
            self.other_purchase.pk,
            purchase_search.context["cl"].result_list.values_list("pk", flat=True),
        )

    def test_staff_cannot_open_or_delete_another_users_documents(self):
        self.login(self.staff_user)
        protected_urls = (
            reverse("admin:invoices_commercialinvoice_change", args=[self.other_invoice.pk]),
            reverse("admin:invoices_commercialinvoice_delete", args=[self.own_invoice.pk]),
            reverse("admin:purchase_purchaseorder_change", args=[self.other_purchase.pk]),
            reverse("admin:purchase_purchaseorder_delete", args=[self.own_purchase.pk]),
        )
        for url in protected_urls:
            self.assertIn(self.client.get(url).status_code, (403, 404))

        self.assertEqual(
            self.client.post(
                reverse("admin:invoices_commercialinvoice_change", args=[self.other_invoice.pk]),
                {},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("admin:purchase_purchaseorder_change", args=[self.other_purchase.pk]),
                {},
            ).status_code,
            403,
        )

    def test_staff_can_open_and_change_own_old_documents(self):
        self.login(self.staff_user)
        invoice_url = reverse(
            "admin:invoices_commercialinvoice_change", args=[self.old_invoice.pk]
        )
        purchase_url = reverse(
            "admin:purchase_purchaseorder_change", args=[self.old_purchase.pk]
        )
        self.assertEqual(self.client.get(invoice_url).status_code, 200)
        self.assertEqual(self.client.get(purchase_url).status_code, 200)

        invoice_admin = admin.site._registry[CommercialInvoice]
        purchase_admin = admin.site._registry[PurchaseOrder]
        request = RequestFactory().get("/admin/")
        request.user = self.staff_user
        self.assertTrue(invoice_admin.has_change_permission(request, self.old_invoice))
        self.assertTrue(purchase_admin.has_change_permission(request, self.old_purchase))

    def test_manager_and_administrator_see_all_documents(self):
        for user in (self.manager, self.administrator):
            self.login(user)
            invoice_response = self.client.get(
                reverse("admin:invoices_commercialinvoice_changelist")
            )
            purchase_response = self.client.get(
                reverse("admin:purchase_purchaseorder_changelist")
            )
            invoice_ids = set(
                invoice_response.context["cl"].result_list.values_list("pk", flat=True)
            )
            purchase_ids = set(
                purchase_response.context["cl"].result_list.values_list("pk", flat=True)
            )
            self.assertTrue(
                {
                    self.own_invoice.pk,
                    self.other_invoice.pk,
                    self.old_invoice.pk,
                    self.unowned_invoice.pk,
                }
                <= invoice_ids
            )
            self.assertTrue(
                {
                    self.own_purchase.pk,
                    self.other_purchase.pk,
                    self.old_purchase.pk,
                    self.unowned_purchase.pk,
                }
                <= purchase_ids
            )

    def test_staff_drafts_are_assigned_to_the_request_user(self):
        self.login(self.staff_user)
        invoice_response = self.client.get(reverse("admin:invoices_commercialinvoice_add"))
        purchase_response = self.client.get(reverse("admin:purchase_purchaseorder_add"))
        self.assertEqual(invoice_response.status_code, 302)
        self.assertEqual(purchase_response.status_code, 302)
        self.assertTrue(
            CommercialInvoice.objects.filter(created_by=self.staff_user).exclude(
                pk__in=[self.own_invoice.pk, self.old_invoice.pk]
            ).exists()
        )
        self.assertTrue(
            PurchaseOrder.objects.filter(created_by=self.staff_user).exclude(
                pk__in=[self.own_purchase.pk, self.old_purchase.pk]
            ).exists()
        )

    def test_staff_company_settings_are_view_only(self):
        self.login(self.staff_user)
        change_url = reverse("admin:company_companysetting_change", args=[self.company.pk])
        self.assertEqual(self.client.get(change_url).status_code, 200)
        self.assertEqual(self.client.post(change_url, {"company_name": "Changed"}).status_code, 403)
        self.company.refresh_from_db()
        self.assertEqual(self.company.company_name, "Test company")

    def test_missing_native_permission_still_denies_access(self):
        restricted_user = User.objects.create_user(
            "staff-without-permissions", password="test-password", is_staff=True
        )
        restricted_user.groups.add(self.staff_group)
        self.login(restricted_user)
        self.assertEqual(
            self.client.get(reverse("admin:products_product_changelist")).status_code,
            403,
        )
