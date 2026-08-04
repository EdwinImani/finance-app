from django.contrib import admin
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum, Q
from django.shortcuts import redirect
from django.urls import Resolver404, resolve
from django.utils.http import urlencode
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.html import format_html
from urllib.parse import parse_qsl, urlparse, urlunparse
from financeapp.admin_mixins import PageSizeAdminMixin, SaveRedirectToWelcomeMixin
from financeapp.access_control import is_staff_role
from .models import Product


# ----------------------
# PART NUMBER FILTER
# ----------------------

class PartNumberFilter(admin.SimpleListFilter):

    title = "Part Number"
    parameter_name = "part_number_status"

    def lookups(self, request, model_admin):
        return (
            ("missing", "Not specified"),
            ("filled", "Specified"),
        )

    def queryset(self, request, queryset):

        if self.value() == "missing":
            return queryset.filter(Q(part_number__isnull=True) | Q(part_number=""))

        if self.value() == "filled":
            return queryset.exclude(Q(part_number__isnull=True) | Q(part_number=""))

        return queryset


# ----------------------
# HS CODE FILTER
# ----------------------

class HSCodeFilter(admin.SimpleListFilter):

    title = "HS Code"
    parameter_name = "hs_code_status"

    def lookups(self, request, model_admin):
        return (
            ("missing", "Not specified"),
            ("filled", "Specified"),
        )

    def queryset(self, request, queryset):

        missing_hs_code = Q(hs_code__isnull=True) | Q(hs_code="") | Q(hs_code="-")

        if self.value() == "missing":
            return queryset.filter(missing_hs_code)

        if self.value() == "filled":
            return queryset.exclude(missing_hs_code)

        return queryset


# ----------------------
# LOW STOCK FILTER
# ----------------------

class LowStockFilter(admin.SimpleListFilter):

    title = "Stock"
    parameter_name = "stock_status"

    def lookups(self, request, model_admin):
        return (
            ("low", "Low stock"),
        )

    def queryset(self, request, queryset):

        if self.value() == "low":
            return queryset.filter(unit_qty__lte=5)

        return queryset


# ----------------------
# PRODUCT ADMIN
# ----------------------

@admin.register(Product)
class ProductAdmin(SaveRedirectToWelcomeMixin, PageSizeAdminMixin, admin.ModelAdmin):
    changelist_template = "admin/products/product/change_list.html"
    change_form_template = "admin/products/product/change_form.html"

    def has_add_permission(self, request):
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return not is_staff_role(request.user) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not is_staff_role(request.user) and super().has_delete_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj)

    list_display = (
        "id",
        "description",
        "part_number_with_hs_code",
        "total_sold",
    )

    search_fields = (
        "=id",
        "description",
        "part_number",
        "hs_code",
        "note",
    )

    search_help_text = "Search by description, part number, HS code, or note"

    ordering = ("description",)

    list_filter = (LowStockFilter, PartNumberFilter, HSCodeFilter)

    def get_paginator(
        self,
        request,
        queryset,
        per_page,
        orphans=0,
        allow_empty_first_page=True,
    ):
        # The Select2 product widget normally fetches only 20 rows at a time.
        # Appending another page while the user is at the bottom makes its
        # scrollbar jump back into the middle. Return the complete filtered
        # product set for autocomplete requests so the scrollbar stays stable
        # and its bottom really is the final product.
        if request.resolver_match and request.resolver_match.url_name == "autocomplete":
            per_page = max(queryset.count(), 1)

        return super().get_paginator(
            request,
            queryset,
            per_page,
            orphans=orphans,
            allow_empty_first_page=allow_empty_first_page,
        )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        return_to = self._get_safe_return_url(request)
        if (
            request.method == "POST"
            and object_id is None
            and return_to
            and self._is_empty_return_product_add(request)
        ):
            return redirect(return_to)

        return super().changeform_view(
            request,
            object_id=object_id,
            form_url=form_url,
            extra_context=extra_context,
        )

    def response_add(self, request, obj, post_url_continue=None):
        return_to = self._get_safe_return_url(request)
        if return_to:
            action = self._get_return_product_action(request)
            if action in {"add", "edit"}:
                self._update_existing_return_item(request, obj, return_to)
                return redirect(self._return_url_with_product(request, obj, return_to))
            self._attach_product_to_return_item(request, obj, return_to)
            return redirect(self._return_url_with_product(request, obj, return_to))
        return super().response_add(request, obj, post_url_continue=post_url_continue)

    def response_change(self, request, obj):
        return_to = self._get_safe_return_url(request)
        if return_to:
            action = self._get_return_product_action(request)
            if action in {"add", "edit"}:
                self._update_existing_return_item(request, obj, return_to)
                return redirect(self._return_url_with_product(request, obj, return_to))
            self._attach_product_to_return_item(request, obj, return_to)
            return redirect(self._return_url_with_product(request, obj, return_to))
        return super().response_change(request, obj)

    def _get_return_product_action(self, request):
        return request.POST.get("_return_product_action") or request.GET.get("_return_product_action")

    def _is_empty_return_product_add(self, request):
        fields = {
            "description": "text",
            "part_number": "text",
            "hs_code": "text",
            "note": "text",
            "unit_qty": "number",
            "sale_price": "number",
            "purchase_price": "number",
        }

        for field, field_type in fields.items():
            value = (request.POST.get(field) or "").strip()
            if field_type == "text" and value:
                return False
            if field_type == "number" and self._posted_number_has_value(value):
                return False

        return True

    def _posted_number_has_value(self, value):
        if not value:
            return False

        normalized = value.replace(",", ".")
        try:
            return float(normalized) != 0
        except ValueError:
            return True

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

    def _return_url_with_product(self, request, product, return_to):
        return_field = request.POST.get("_return_field") or request.GET.get("_return_field")
        if not return_field:
            return return_to

        return self._url_with_query(
            return_to,
            {
                "_selected_product_field": return_field,
                "_selected_product_id": product.pk,
                "_selected_product_label": str(product),
            },
        )

    def _attach_product_to_return_item(self, request, product, return_to, force_new=False):
        return_field = request.POST.get("_return_field") or request.GET.get("_return_field")
        if not return_field or not return_field.endswith("-product"):
            return

        parsed = urlparse(return_to)
        try:
            match = resolve(parsed.path)
        except Resolver404:
            return

        object_id = match.kwargs.get("object_id")
        target = self._product_return_target(match.url_name)
        if not object_id or not target:
            return

        parent_app, parent_model, item_app, item_model, parent_field, price_field = target

        try:
            parent_cls = apps.get_model(parent_app, parent_model)
            item_cls = apps.get_model(item_app, item_model)
            parent = parent_cls.objects.get(pk=object_id)
        except (LookupError, ObjectDoesNotExist):
            return

        item_id = "" if force_new else request.POST.get("_return_item_id") or request.GET.get("_return_item_id")
        item = None
        if item_id:
            try:
                item = item_cls.objects.get(pk=item_id, **{parent_field: parent})
            except (ValueError, ObjectDoesNotExist):
                item = None

        if item is None:
            item = item_cls(**{parent_field: parent})

        item.product = product
        if hasattr(item, "description") and not item.description:
            item.description = product.description
        if hasattr(item, "part_number") and not item.part_number:
            item.part_number = product.part_number or ""
        if hasattr(item, "hs_code") and not item.hs_code:
            item.hs_code = product.hs_code or "-"
        if hasattr(item, "quantity") and not item.quantity:
            item.quantity = 1
        if hasattr(item, "unit_price") and not item.unit_price:
            item.unit_price = getattr(product, price_field)
        item.save()

    def _update_existing_return_item(self, request, product, return_to):
        return_field = request.POST.get("_return_field") or request.GET.get("_return_field")
        item_id = request.POST.get("_return_item_id") or request.GET.get("_return_item_id")
        if not return_field or not return_field.endswith("-product") or not item_id:
            return

        parsed = urlparse(return_to)
        try:
            match = resolve(parsed.path)
        except Resolver404:
            return

        object_id = match.kwargs.get("object_id")
        target = self._product_return_target(match.url_name)
        if not object_id or not target:
            return

        parent_app, parent_model, item_app, item_model, parent_field, price_field = target

        try:
            parent_cls = apps.get_model(parent_app, parent_model)
            item_cls = apps.get_model(item_app, item_model)
            parent = parent_cls.objects.get(pk=object_id)
            item = item_cls.objects.get(pk=item_id, **{parent_field: parent})
        except (LookupError, ValueError, ObjectDoesNotExist):
            return

        item.product = product
        if hasattr(item, "description"):
            item.description = product.description
        if hasattr(item, "part_number"):
            item.part_number = product.part_number or ""
        if hasattr(item, "hs_code") and not item.hs_code:
            item.hs_code = product.hs_code or "-"
        if hasattr(item, "unit_price"):
            item.unit_price = getattr(product, price_field)
        item.save()

    def _product_return_target(self, url_name):
        targets = {
            "invoices_proformainvoice_change": (
                "invoices",
                "proformainvoice",
                "invoices",
                "proformainvoiceitem",
                "invoice",
                "sale_price",
            ),
            "invoices_commercialinvoice_change": (
                "invoices",
                "commercialinvoice",
                "invoices",
                "commercialinvoiceitem",
                "invoice",
                "sale_price",
            ),
            "purchase_purchaseorder_change": (
                "purchase",
                "purchaseorder",
                "purchase",
                "purchaseorderitem",
                "purchase_order",
                "purchase_price",
            ),
        }
        return targets.get(url_name)

    def _url_with_query(self, url, params):
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.update(params)
        return urlunparse(parsed._replace(query=urlencode(query)))

    # ----------------------
    # PART NUMBER DISPLAY
    # ----------------------

    def part_number_with_hs_code(self, obj):
        part_number = obj.part_number or "Not specified"
        hs_code = obj.hs_code or "Not specified"
        return format_html(
            '<span class="product-part-number">{}</span>'
            '<span class="product-hs-code">HS Code: {}</span>',
            part_number,
            hs_code,
        )

    part_number_with_hs_code.short_description = "Part Number"
    part_number_with_hs_code.admin_order_field = "part_number"

    def hs_code_display(self, obj):
        return obj.hs_code if obj.hs_code else "Not specified"

    hs_code_display.short_description = "HS Code"

    # ----------------------
    # QUERYSET WITH SALES
    # ----------------------

    def get_queryset(self, request):

        qs = super().get_queryset(request)

        return qs.annotate(
            sold_proforma=Sum("proforma_items__quantity"),
            sold_commercial=Sum("commercial_items__quantity"),
        )

    def get_search_results(self, request, queryset, search_term):

        queryset, may_have_duplicates = super().get_search_results(
            request,
            queryset,
            search_term,
        )

        term = (search_term or "").strip()

        if not term:
            return queryset, may_have_duplicates

        extra_matches = self.model.objects.filter(
            Q(part_number__iexact=term) |
            Q(part_number__istartswith=term) |
            Q(part_number__icontains=term) |
            Q(description__istartswith=term) |
            Q(description__icontains=term) |
            Q(note__icontains=term)
        )

        for word in term.split():
            extra_matches = extra_matches.filter(
                Q(part_number__istartswith=word) |
                Q(part_number__icontains=word) |
                Q(description__istartswith=word) |
                Q(description__icontains=word) |
                Q(note__icontains=word)
            )

        return (queryset | extra_matches).distinct(), True

    # ----------------------
    # TOTAL SOLD
    # ----------------------

    def total_sold(self, obj):

        proforma = obj.sold_proforma or 0
        commercial = obj.sold_commercial or 0

        return proforma + commercial

    total_sold.short_description = "Total Sold"
