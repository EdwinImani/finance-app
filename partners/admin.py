from django.contrib import admin
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.forms.formsets import all_valid
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import Resolver404, path, resolve, reverse
from django.utils.http import urlencode
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import parse_qsl, urlparse, urlunparse
from financeapp.admin_mixins import PageSizeAdminMixin, SaveRedirectToWelcomeMixin
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
class PartnerAdmin(SaveRedirectToWelcomeMixin, PageSizeAdminMixin, admin.ModelAdmin):
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
        "partner_type",
        "email",
        "fax",
        "website",
        "addresses__address",
        "phones__phone_number",
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
            change_url = reverse("admin:partners_partner_change", args=[draft.pk])
            return_to = self._get_safe_return_url(request)
            if return_to:
                query = {"_return_to": return_to}
                return_field = request.GET.get("_return_field")
                if return_field:
                    query["_return_field"] = return_field
                change_url = f"{change_url}?{urlencode(query)}"
            return redirect(change_url)

        return super().add_view(request, form_url, extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        return_to = self._get_safe_return_url(request)
        if return_to:
            self._attach_partner_to_return_object(request, obj, return_to)
            return redirect(self._return_url_with_partner(request, obj, return_to))
        return super().response_add(request, obj, post_url_continue=post_url_continue)

    def response_change(self, request, obj):
        return_to = self._get_safe_return_url(request)
        if return_to:
            self._attach_partner_to_return_object(request, obj, return_to)
            return redirect(self._return_url_with_partner(request, obj, return_to))
        return super().response_change(request, obj)

    def _get_safe_return_url(self, request):
        return_to = request.POST.get("_return_to") or request.GET.get("_return_to")
        if not return_to:
            return ""

        if url_has_allowed_host_and_scheme(
            return_to,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return return_to

        return ""

    def _return_url_with_partner(self, request, partner, return_to):
        return_field = request.POST.get("_return_field") or request.GET.get("_return_field")
        if not return_field:
            return return_to

        return self._url_with_query(
            return_to,
            {
                "_selected_partner_field": return_field,
                "_selected_partner_id": partner.pk,
                "_selected_partner_label": str(partner),
            },
        )

    def _url_with_query(self, url, params):
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.update(params)
        return urlunparse(parsed._replace(query=urlencode(query)))

    def _attach_partner_to_return_object(self, request, partner, return_to):
        return_field = request.POST.get("_return_field") or request.GET.get("_return_field")
        allowed_targets = {
            "id_importer": ("invoices", "proformainvoice", "importer"),
            "id_end_user": ("invoices", "proformainvoice", "end_user"),
            "id_seller": ("purchase", "purchaseorder", "seller"),
            "id_requester": ("purchase", "purchaseorder", "requester"),
        }
        commercial_targets = {
            "id_importer": ("invoices", "commercialinvoice", "importer"),
            "id_end_user": ("invoices", "commercialinvoice", "end_user"),
        }

        parsed = urlparse(return_to)
        try:
            match = resolve(parsed.path)
        except Resolver404:
            return

        object_id = match.kwargs.get("object_id")
        if not object_id:
            return

        target = allowed_targets.get(return_field)
        if match.url_name == "invoices_commercialinvoice_change":
            target = commercial_targets.get(return_field)

        if not target:
            return

        app_label, model_name, field_name = target
        expected_url_name = f"{app_label}_{model_name}_change"
        if match.url_name != expected_url_name:
            return

        try:
            model = apps.get_model(app_label, model_name)
            document = model.objects.get(pk=object_id)
        except (LookupError, ObjectDoesNotExist):
            return

        setattr(document, field_name, partner)
        document.save(update_fields=[field_name])

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
