from django.contrib import admin
from financeapp.admin_mixins import PageSizeAdminMixin
from .models import Partner, PartnerAddress, PartnerPhone


# ----------------------
# PARTNER ADDRESS INLINE
# ----------------------

class PartnerAddressInline(admin.TabularInline):

    model = PartnerAddress
    extra = 1


# ----------------------
# PARTNER PHONE INLINE
# ----------------------

class PartnerPhoneInline(admin.TabularInline):

    model = PartnerPhone
    extra = 1


# ----------------------
# PARTNER ADMIN
# ----------------------

@admin.register(Partner)
class PartnerAdmin(PageSizeAdminMixin, admin.ModelAdmin):
    changelist_template = "admin/partners/partner/change_list.html"

    list_display = (
        "description",
        "partner_type",
        "get_phone",
        "email",
    )

    search_fields = (
        "description",
        "email",
    )

    list_filter = (
        "partner_type",
    )

    inlines = [
        PartnerAddressInline,
        PartnerPhoneInline
    ]

    # ----------------------
    # AUTO PARTNER TYPE
    # ----------------------

    def get_changeform_initial_data(self, request):

        initial = super().get_changeform_initial_data(request)

        partner_type = request.GET.get("partner_type")

        if partner_type in [
            "seller",
            "requester",
            "importer",
            "enduser",
        ]:
            initial["partner_type"] = partner_type

        return initial


    # ----------------------
    # PHONE DISPLAY
    # ----------------------

    def get_phone(self, obj):

        phone = obj.phones.first()

        if phone:
            return phone.phone_number

        return "-"

    get_phone.short_description = "Telephone"
