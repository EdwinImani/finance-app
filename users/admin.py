from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.contrib.admin.sites import NotRegistered

from financeapp.admin_mixins import SaveRedirectToWelcomeMixin


class WelcomeRedirectUserAdmin(SaveRedirectToWelcomeMixin, UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "is_active",
        "last_login",
    )
    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "groups",
    )
    fieldsets = (
        (
            "Informations principales",
            {
                "fields": (
                    "username",
                    "password",
                    ("first_name", "last_name"),
                    "email",
                    "is_active",
                )
            },
        ),
        (
            "Permissions et groupes",
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Dates importantes",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )
    readonly_fields = (
        "last_login",
        "date_joined",
    )
    filter_horizontal = (
        "groups",
        "user_permissions",
    )


class WelcomeRedirectGroupAdmin(SaveRedirectToWelcomeMixin, GroupAdmin):
    list_display = (
        "name",
        "permissions_count",
    )
    search_fields = ("name",)
    fieldsets = (
        (
            "Nom du groupe",
            {
                "fields": ("name",),
            },
        ),
        (
            "Permissions",
            {
                "fields": ("permissions",),
            },
        ),
    )
    filter_horizontal = ("permissions",)

    def permissions_count(self, obj):
        return obj.permissions.count()

    permissions_count.short_description = "Nombre de permissions"


for model in (User, Group):
    try:
        admin.site.unregister(model)
    except NotRegistered:
        pass


admin.site.register(User, WelcomeRedirectUserAdmin)
admin.site.register(Group, WelcomeRedirectGroupAdmin)
