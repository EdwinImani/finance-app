from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.sites import NotRegistered
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html

from financeapp.admin_mixins import SaveRedirectToWelcomeMixin
from financeapp.access_control import is_administrator
from .forms import AdminUserChangeForm, AdminUserCreationForm
from invoices.models import CommercialInvoice
from purchase.models import PurchaseOrder


LogEntry._meta.verbose_name = "History"
LogEntry._meta.verbose_name_plural = "History"


def ensure_document_report_permissions():
    """Ensure custom report permissions exist before rendering security forms."""
    definitions = (
        (
            CommercialInvoice,
            "view_commercial_invoice_reports",
            "Can access Commercial Invoice reports",
        ),
        (
            PurchaseOrder,
            "view_purchase_order_reports",
            "Can access Purchase Order reports",
        ),
    )
    for model, codename, name in definitions:
        content_type = ContentType.objects.get_for_model(model)
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        if permission.name != name:
            permission.name = name
            permission.save(update_fields=["name"])


class SecurityAdminAccessMixin:
    """Keep auth administration unconditional for superusers."""

    def _can_manage_security(self, request):
        if request.user.is_superuser:
            return True
        return is_administrator(request.user)

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        return self._can_manage_security(request)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._can_manage_security(request)

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return self._can_manage_security(request)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._can_manage_security(request)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._can_manage_security(request)

    def get_model_perms(self, request):
        if request.user.is_superuser:
            return {"add": True, "change": True, "delete": True, "view": True}
        allowed = self._can_manage_security(request)
        return {"add": allowed, "change": allowed, "delete": allowed, "view": allowed}

    def get_queryset(self, request):
        if request.user.is_superuser:
            return self.model._default_manager.all()
        if self._can_manage_security(request):
            return super().get_queryset(request)
        return self.model._default_manager.none()


class WelcomeRedirectUserAdmin(
    SecurityAdminAccessMixin,
    SaveRedirectToWelcomeMixin,
    UserAdmin,
):
    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    add_fieldsets = (
        (
            "Compte et mot de passe",
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    ("first_name", "last_name"),
                    "email",
                    "is_active",
                    "is_staff",
                    "groups",
                    "can_view_all_documents",
                ),
            },
        ),
    )

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
                    "can_view_all_documents",
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


class WelcomeRedirectGroupAdmin(
    SecurityAdminAccessMixin,
    SaveRedirectToWelcomeMixin,
    GroupAdmin,
):
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

    def add_view(self, request, form_url="", extra_context=None):
        ensure_document_report_permissions()
        return super().add_view(request, form_url, extra_context)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        ensure_document_report_permissions()
        return super().changeform_view(request, object_id, form_url, extra_context)

    def permissions_count(self, obj):
        return obj.permissions.count()

    permissions_count.short_description = "Nombre de permissions"


@admin.register(LogEntry)
class AdminHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "action_time",
        "user",
        "action_label",
        "content_type",
        "object_link",
        "change_message",
    )
    list_filter = (
        "action_flag",
        "user",
        "content_type",
        "action_time",
    )
    search_fields = (
        "user__username",
        "user__email",
        "object_repr",
        "change_message",
    )
    date_hierarchy = "action_time"
    ordering = ("-action_time",)
    readonly_fields = (
        "action_time",
        "user",
        "content_type",
        "object_id",
        "object_repr",
        "action_flag",
        "change_message",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("admin.view_logentry")

    def has_delete_permission(self, request, obj=None):
        return False

    def action_label(self, obj):
        labels = {
            1: "Added",
            2: "Changed",
            3: "Deleted",
        }
        return labels.get(obj.action_flag, obj.action_flag)

    action_label.short_description = "Action"
    action_label.admin_order_field = "action_flag"

    def object_link(self, obj):
        if not obj.content_type or not obj.object_id:
            return obj.object_repr or "-"

        url_name = (
            f"admin:{obj.content_type.app_label}_"
            f"{obj.content_type.model}_change"
        )
        try:
            url = reverse(url_name, args=(obj.object_id,))
        except NoReverseMatch:
            return obj.object_repr or "-"

        return format_html('<a href="{}">{}</a>', url, obj.object_repr or obj.object_id)

    object_link.short_description = "Object"


for model in (User, Group):
    try:
        admin.site.unregister(model)
    except NotRegistered:
        pass


admin.site.register(User, WelcomeRedirectUserAdmin)
admin.site.register(Group, WelcomeRedirectGroupAdmin)
