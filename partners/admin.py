from django.contrib import admin
from django.forms.formsets import all_valid
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils import timezone
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
    change_form_template = "admin/partners/partner/change_form.html"

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

    ordering = ("description",)

    list_filter = (
        "partner_type",
    )

    inlines = [
        PartnerAddressInline,
        PartnerPhoneInline
    ]

    class Media:
        js = ("admin/js/invoice_autosave.js",)

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        context["invoice_autosave_url"] = self.get_partner_autosave_url(obj) if obj and obj.pk else ""
        return super().render_change_form(request, context, add, change, form_url, obj)

    def get_partner_autosave_url(self, obj):
        return reverse("admin:partners_partner_autosave", args=[obj.pk])

    def create_draft_partner(self, request):
        partner_type = request.GET.get("partner_type")
        valid_types = {choice[0] for choice in Partner.PARTNER_TYPES}

        if partner_type not in valid_types:
            partner_type = "importer"

        return Partner.objects.create(
            description="New partner",
            partner_type=partner_type,
        )

    def add_view(self, request, form_url="", extra_context=None):
        if request.method == "GET" and not request.GET.get("_popup"):
            draft = self.create_draft_partner(request)
            return redirect(reverse("admin:partners_partner_change", args=[draft.pk]))

        return super().add_view(request, form_url, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/autosave/",
                self.admin_site.admin_view(self.autosave),
                name="partners_partner_autosave",
            ),
        ]
        return custom_urls + urls

    def autosave(self, request, object_id):
        if request.method != "POST":
            return JsonResponse({"ok": False, "error": "POST required."}, status=405)

        obj = get_object_or_404(Partner, pk=object_id)
        form_class = self.get_form(request, obj, change=True)
        post_data = request.POST.copy()
        self._remove_new_inline_forms_from_autosave(post_data)
        form = form_class(post_data, request.FILES, instance=obj)

        original_post = request.POST
        request.POST = post_data
        try:
            formsets, inline_instances = self._create_formsets(request, form.instance, change=True)
        finally:
            request.POST = original_post

        if form.is_valid() and all_valid(formsets):
            new_object = self.save_form(request, form, change=True)
            self.save_model(request, new_object, form, change=True)
            form.save_m2m()
            self.save_related(request, form, formsets, change=True)
            return JsonResponse(
                {
                    "ok": True,
                    "saved_at": timezone.localtime().strftime("%d/%m/%Y %H:%M:%S"),
                    "partner": new_object.description or "",
                }
            )

        errors = {"form": form.errors}
        inline_errors = []
        for inline, formset in zip(inline_instances, formsets):
            if formset.non_form_errors() or any(child.errors for child in formset.forms):
                inline_errors.append(
                    {
                        "inline": inline.__class__.__name__,
                        "non_form_errors": list(formset.non_form_errors()),
                        "errors": [child.errors for child in formset.forms if child.errors],
                    }
                )
        errors["inlines"] = inline_errors
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    def _remove_new_inline_forms_from_autosave(self, post_data):
        prefixes = [
            key[:-len("-TOTAL_FORMS")]
            for key in post_data.keys()
            if key.endswith("-TOTAL_FORMS")
        ]

        for prefix in prefixes:
            total_key = f"{prefix}-TOTAL_FORMS"
            initial_key = f"{prefix}-INITIAL_FORMS"
            if initial_key not in post_data:
                continue

            try:
                total_forms = int(post_data.get(total_key) or 0)
                initial_forms = int(post_data.get(initial_key) or 0)
            except (TypeError, ValueError):
                continue

            if total_forms <= initial_forms:
                continue

            for index in range(initial_forms, total_forms):
                form_prefix = f"{prefix}-{index}-"
                for key in list(post_data.keys()):
                    if key.startswith(form_prefix):
                        post_data.pop(key, None)
            post_data[total_key] = str(initial_forms)

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
