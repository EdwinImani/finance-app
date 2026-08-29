from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from financeapp.admin_mixins import SaveRedirectToWelcomeMixin
from financeapp.access_control import is_staff_role
from .models import CompanySetting


@admin.register(CompanySetting)
class CompanySettingAdmin(SaveRedirectToWelcomeMixin, admin.ModelAdmin):
    change_form_template = "admin/company/companysetting/change_form.html"
    save_redirect_url = "/admin/"

    list_display = (
        "default_badge",
        "company_name",
        "year",
        "currency",
        "commercial_invoice_template",
        "vat_amount",
        "company_phone",
        "company_email",
    )

    list_filter = (
        "is_default",
        "currency",
        "commercial_invoice_template",
    )

    search_fields = (
        "company_name",
        "company_email",
        "bank",
        "iban",
    )

    readonly_fields = (
        "logo_preview",
        "settings_summary",
        "login_password_panel",
    )

    def has_add_permission(self, request):
        if is_staff_role(request.user):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if is_staff_role(request.user):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if is_staff_role(request.user):
            return False
        return super().has_delete_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if is_staff_role(request.user):
            readonly.extend(
                field.name for field in self.model._meta.fields if field.editable
            )
        return tuple(dict.fromkeys(readonly))

    def _get_return_url(self, request):
        return self.save_redirect_url

    fieldsets = (

        ("Overview", {
            "fields": (
                "settings_summary",
                "login_password_panel",
            )
        }),

        ("Company Information", {
            "fields": (
                "company_logo",
                "logo_preview",
                "is_default",
                "year",
                "company_name",
                "president",
                "company_email",
                ("company_phone", "company_fax"),
            )
        }),

        ("Address", {
            "fields": (
                "company_address",
                "address",
            )
        }),

        ("Legal Information", {
            "fields": (
                ("siren", "vat_number"),
            )
        }),

        ("Bank Information", {
            "fields": (
                "bank",
                ("iban", "bic"),
            )
        }),

        ("Documents Settings", {
            "fields": (
                "commercial_invoice_template",
                ("currency", "vat_amount"),
                "delivery_time",
                "terms_conditions",
                "proforma_validity",
            )
        }),

        ("Notes / Footer", {
            "fields": (
                "note",
                "footer_order",
                "footer_invoice",
                "invoice_note",
            )
        }),
    )

    def default_badge(self, obj):
        if obj.is_default:
            return format_html('<span class="company-default-badge">{}</span>', "Default")
        return "-"

    default_badge.short_description = "Default"
    default_badge.admin_order_field = "is_default"

    def logo_preview(self, obj):
        if not obj or not obj.company_logo:
            return format_html(
                '<div class="company-logo-empty">{}</div>',
                "No logo uploaded yet.",
            )

        return format_html(
            '<div class="company-logo-preview-wrap">'
            '<img src="{}" alt="Company logo" class="company-logo-preview" />'
            '</div>',
            obj.company_logo.url,
        )

    logo_preview.short_description = "Logo Preview"

    def settings_summary(self, obj):
        if not obj:
            return format_html(
                '<div class="company-settings-summary">'
                '<div class="company-summary-card"><strong>Company</strong><span>{}</span></div>'
                '<div class="company-summary-card"><strong>Currency</strong><span>{}</span></div>'
                '<div class="company-summary-card"><strong>Commercial Template</strong><span>{}</span></div>'
                '<div class="company-summary-card"><strong>VAT</strong><span>{}</span></div>'
                '<div class="company-summary-card"><strong>Proforma Validity</strong><span>{}</span></div>'
                "</div>",
                "Not set yet",
                "-",
                "-",
                "-",
                "-",
            )

        return format_html(
            '<div class="company-settings-summary">'
            '<div class="company-summary-card"><strong>Company</strong><span>{}</span></div>'
            '<div class="company-summary-card"><strong>Currency</strong><span>{}</span></div>'
            '<div class="company-summary-card"><strong>Commercial Template</strong><span>{}</span></div>'
            '<div class="company-summary-card"><strong>VAT</strong><span>{}%</span></div>'
            '<div class="company-summary-card"><strong>Proforma Validity</strong><span>{} days</span></div>'
            "</div>",
            obj.company_name or "-",
            obj.get_currency_display() if obj.currency else "-",
            obj.get_commercial_invoice_template_display() if obj.commercial_invoice_template else "-",
            obj.vat_amount if obj.vat_amount is not None else "-",
            obj.proforma_validity if obj.proforma_validity is not None else "-",
        )

    settings_summary.short_description = "Summary"

    def login_password_panel(self, obj):
        password_url = reverse("admin:password_change")

        return format_html(
            '<div class="company-login-security">'
            '<div>'
            '<strong>Login password</strong>'
            '<span>Change the password used to connect to this admin account.</span>'
            '</div>'
            '<a class="company-password-button" href="{}">Change password</a>'
            '</div>',
            password_url,
        )

    login_password_panel.short_description = "Security"
