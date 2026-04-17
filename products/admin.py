from django.contrib import admin
from django.db.models import Sum, Q
from financeapp.admin_mixins import PageSizeAdminMixin
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
class ProductAdmin(PageSizeAdminMixin, admin.ModelAdmin):
    changelist_template = "admin/products/product/change_list.html"

    list_display = (
        "description",
        "part_number_display",
        "hs_code_display",
        "unit_qty",
        "sale_price",
        "total_sold",
    )

    search_fields = (
        "description",
        "part_number",
        "hs_code",
        "note",
    )

    search_help_text = "Search by part number, description, or note"

    ordering = ("description",)

    list_filter = (LowStockFilter, PartNumberFilter)

    # ----------------------
    # PART NUMBER DISPLAY
    # ----------------------

    def part_number_display(self, obj):
        return obj.part_number if obj.part_number else "Not specified"

    part_number_display.short_description = "Part Number"

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
            Q(part_number__icontains=term) |
            Q(description__icontains=term) |
            Q(note__icontains=term)
        )

        for word in term.split():
            extra_matches = extra_matches.filter(
                Q(part_number__icontains=word) |
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
