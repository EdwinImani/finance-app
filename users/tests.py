from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.test import TestCase


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
