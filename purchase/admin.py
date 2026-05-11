from decimal import Decimal
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.contrib import admin
from django import forms
from django.forms.formsets import all_valid
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import path
from django.urls import reverse
from django.utils import timezone
from financeapp.admin_mixins import PageSizeAdminMixin
from financeapp.pdf_rendering import get_pdf_fallback_reason, should_try_weasyprint
from invoices.pdf_builder import build_purchase_order_pdf, build_purchase_report_pdf

from company.models import CompanySetting
from partners.models import Partner
from products.models import Product

from .models import PurchaseOrder, PurchaseOrderItem


# ----------------------
# PURCHASE ORDER ITEMS
# ----------------------

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

    fields = (
        "product",
        "description",
        "part_number",
        "quantity",
        "unit_price",
        "total_line",
    )

    readonly_fields = (
        "part_number",
        "total_line",
    )

    autocomplete_fields = ("product",)


class PurchaseOrderAdminForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = CompanySetting.objects.first()

        if company and not self.instance.pk:
            self.fields["vat_percent"].initial = company.vat_amount
            self.fields["purchase_date"].initial = self._get_default_company_date(company.year)

    def _get_default_company_date(self, year):
        today = timezone.now().date()
        try:
            return today.replace(year=year)
        except ValueError:
            return today.replace(year=year, day=28)

    def clean_vat_percent(self):
        vat_percent = self.cleaned_data.get("vat_percent")

        if vat_percent in (None, ""):
            company = CompanySetting.objects.first()
            if company:
                return company.vat_amount

        return vat_percent


# ----------------------
# PURCHASE ORDER ADMIN
# ----------------------

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(PageSizeAdminMixin, admin.ModelAdmin):
    changelist_template = "admin/purchase/purchaseorder/change_list.html"
    change_form_template = "admin/purchase/purchaseorder/change_form.html"
    list_max_show_all = 100
    form = PurchaseOrderAdminForm

    readonly_fields = (
        "purchase_number",
        "gross_value_display",
        "vat_amount_display",
        "total_amount_display",
    )

    fieldsets = (
        ("Order Overview", {
            "fields": (
                "purchase_number",
                "purchase_date",
                "seller",
                ("sent_by", "shipment"),
            )
        }),
        ("Financial Settings", {
            "fields": (
                ("freight", "vat_percent"),
                ("gross_value_display", "vat_amount_display", "total_amount_display"),
            )
        }),
        ("Commercial Terms", {
            "fields": (
                "sales_condition",
                "payment_condition",
                "delivery_terms",
            )
        }),
    )

    list_display = (
        "purchase_number",
        "purchase_date_display",
        "seller",
        "amount_display",
    )

    list_filter = ("purchase_date", "seller")
    search_fields = (
        "purchase_number",
        "seller__description",
        "sent_by",
    )

    autocomplete_fields = ("seller",)

    inlines = [PurchaseOrderItemInline]

    class Media:
        js = (
            "admin/js/product_autofill.js",
            "admin/js/purchase_partner_type.js",
            "admin/js/invoice_autosave.js",
        )

    def get_default_purchase_date(self):
        company = CompanySetting.objects.first()
        today = timezone.now().date()
        if not company or not company.year:
            return today
        try:
            return today.replace(year=company.year)
        except ValueError:
            return today.replace(year=company.year, day=28)

    def get_default_vat_percent(self):
        company = CompanySetting.objects.first()
        return company.vat_amount if company else Decimal("0.00")

    def create_draft_purchase_order(self):
        return PurchaseOrder.objects.create(
            purchase_date=self.get_default_purchase_date(),
            vat_percent=self.get_default_vat_percent(),
        )

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        context["invoice_autosave_url"] = self.get_purchase_autosave_url(obj) if obj and obj.pk else ""
        context["purchase_pdf_url"] = self.get_purchase_pdf_url(obj) if obj and obj.pk else ""
        return super().render_change_form(request, context, add, change, form_url, obj)

    def add_view(self, request, form_url="", extra_context=None):
        if request.method == "GET" and not request.GET.get("_popup"):
            draft = self.create_draft_purchase_order()
            return redirect(reverse("admin:purchase_purchaseorder_change", args=[draft.pk]))
        return super().add_view(request, form_url, extra_context)

    def get_purchase_autosave_url(self, obj):
        return reverse("admin:purchase_purchaseorder_autosave", args=[obj.pk])

    def get_purchase_pdf_url(self, obj):
        return reverse("admin:purchase_purchaseorder_pdf", args=[obj.pk])

    def get_company_year(self):
        company = CompanySetting.objects.first()
        return company.year if company and company.year else None

    def has_explicit_year_filter(self, request, field_name):
        return any(key.startswith(field_name) for key in request.GET.keys())

    def should_apply_default_year_filter(self, request):
        match = getattr(request, "resolver_match", None)
        return bool(match and match.url_name and match.url_name.endswith("_changelist"))

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        company_year = self.get_company_year()
        if (
            company_year and
            self.should_apply_default_year_filter(request) and
            not self.has_explicit_year_filter(request, "purchase_date")
        ):
            queryset = queryset.filter(purchase_date__year=company_year)
        return queryset

    def purchase_date_display(self, obj):
        if obj.purchase_date:
            return obj.purchase_date.strftime("%d/%m/%Y")
        return "-"

    purchase_date_display.short_description = "Date"
    purchase_date_display.admin_order_field = "purchase_date"

    def amount_display(self, obj):
        return obj.total_amount()

    amount_display.short_description = "Amount"

    def gross_value_display(self, obj):
        return obj.gross_value() if obj.pk else Decimal("0.00")

    gross_value_display.short_description = "Gross Value"

    def vat_amount_display(self, obj):
        return obj.vat_amount() if obj.pk else Decimal("0.00")

    vat_amount_display.short_description = "VAT Amount"

    def total_amount_display(self, obj):
        return obj.total_amount() if obj.pk else Decimal("0.00")

    total_amount_display.short_description = "Total Amount"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/autosave/",
                self.admin_site.admin_view(self.autosave),
                name="purchase_purchaseorder_autosave",
            ),
            path(
                "<int:object_id>/pdf/",
                self.admin_site.admin_view(self.export_purchase_pdf),
                name="purchase_purchaseorder_pdf",
            ),
            path(
                "report/",
                self.admin_site.admin_view(self.purchase_report),
                name="purchase_report",
            ),
            path(
                "report/pdf/",
                self.admin_site.admin_view(self.purchase_report_pdf),
                name="purchase_report_pdf",
            ),
        ]
        return custom_urls + urls

    def autosave(self, request, object_id):
        if request.method != "POST":
            return JsonResponse({"ok": False, "error": "POST required."}, status=405)

        obj = get_object_or_404(PurchaseOrder, pk=object_id)
        form_class = self.get_form(request, obj, change=True)
        form = form_class(request.POST, request.FILES, instance=obj)
        formsets, inline_instances = self._create_formsets(request, form.instance, change=True)

        if form.is_valid() and all_valid(formsets):
            new_object = self.save_form(request, form, change=True)
            self.save_model(request, new_object, form, change=True)
            form.save_m2m()
            self.save_related(request, form, formsets, change=True)
            return JsonResponse(
                {
                    "ok": True,
                    "saved_at": timezone.localtime().strftime("%d/%m/%Y %H:%M:%S"),
                    "purchase_number": new_object.purchase_number or "",
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

    def build_partner_context(self, partner):
        if not partner:
            return {
                "name": "-",
                "addresses": [],
                "phones": [],
                "email": "",
                "website": "",
                "fax": "",
            }

        return {
            "name": partner.description,
            "addresses": [address.address for address in partner.addresses.all()],
            "phones": [phone.phone_number for phone in partner.phones.all() if phone.phone_number],
            "email": partner.email,
            "website": partner.website,
            "fax": partner.fax,
        }

    def build_company_partner_context(self, company):
        if not company:
            return self.build_partner_context(None)

        addresses = []
        if company.company_address:
            addresses.append(company.company_address)
        if company.address and company.address not in addresses:
            addresses.append(company.address)

        phones = [company.company_phone] if company.company_phone else []

        return {
            "name": company.company_name or "-",
            "addresses": addresses,
            "phones": phones,
            "email": company.company_email,
            "website": "",
            "fax": company.company_fax,
        }

    def get_purchase_items_for_pdf(self, obj):
        return [
            {
                "index": index,
                "description": item.description or (item.product.description if item.product else "-"),
                "part_number": item.part_number or (item.product.part_number if item.product and item.product.part_number else "-"),
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_amount": item.total_line(),
                "vat_percent": obj.vat_percent,
            }
            for index, item in enumerate(obj.items.select_related("product"), start=1)
        ]

    def export_purchase_pdf(self, request, object_id):
        obj = get_object_or_404(
            PurchaseOrder.objects.select_related("seller", "requester").prefetch_related(
                "items__product",
                "seller__addresses",
                "seller__phones",
                "requester__addresses",
                "requester__phones",
            ),
            pk=object_id,
        )
        company = CompanySetting.objects.first()
        try:
            pdf_bytes = build_purchase_order_pdf(
                purchase_order=obj,
                company=company,
                items=self.get_purchase_items_for_pdf(obj),
                seller=self.build_partner_context(obj.seller),
                requester={
                    "name": company.company_name if company and company.company_name else "-",
                    "addresses": [],
                    "phones": [],
                    "email": "",
                    "website": "",
                    "fax": "",
                },
                requester_is_explicit=False,
                currency=company.currency if company else "EUR",
            )
        except Exception as exc:
            return HttpResponse(
                f"PDF generation failed: {exc}",
                content_type="text/plain; charset=utf-8",
                status=500,
            )

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{obj.purchase_number or "purchase-order"}.pdf"'
        return response

    def get_purchase_report_pdf_url(self, request):
        query_string = request.GET.urlencode()
        base_url = reverse("admin:purchase_report_pdf")
        return f"{base_url}?{query_string}" if query_string else base_url

    def _pdf_link_callback(self, uri, rel):
        parsed = urlparse(uri)
        path = unquote(parsed.path or uri)

        if path.startswith(settings.MEDIA_URL):
            return str(Path(settings.MEDIA_ROOT) / path.removeprefix(settings.MEDIA_URL))

        if path.startswith(settings.STATIC_URL):
            static_roots = []
            static_root = getattr(settings, "STATIC_ROOT", None)
            if static_root:
                static_roots.append(Path(static_root))
            static_roots.extend(Path(root) for root in getattr(settings, "STATICFILES_DIRS", []))

            relative_path = path.removeprefix(settings.STATIC_URL)
            for root in static_roots:
                candidate = root / relative_path
                if candidate.exists():
                    return str(candidate)

        if parsed.scheme == "file":
            return parsed.path

        return uri

    def _build_pdf_with_weasyprint(self, html_string, base_url):
        from weasyprint import HTML

        return HTML(string=html_string, base_url=base_url).write_pdf()

    def _build_pdf_with_xhtml2pdf(self, html_string):
        from xhtml2pdf import pisa

        result = BytesIO()
        pdf = pisa.CreatePDF(
            src=html_string,
            dest=result,
            link_callback=self._pdf_link_callback,
        )
        if pdf.err:
            raise RuntimeError("xhtml2pdf could not render the purchase report.")
        return result.getvalue()

    def _build_report_context(self, request):
        company = CompanySetting.objects.first()
        sellers = Partner.objects.filter(partner_type="seller").order_by("description")
        products = Product.objects.all().order_by("description")

        selected_sellers = request.GET.getlist("importers")
        selected_products = request.GET.getlist("products")
        year = request.GET.get("year")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")
        company_year = self.get_company_year()

        if not year and not date_from and not date_to and company_year:
            year = str(company_year)

        line_total = ExpressionWrapper(
            F("items__quantity") * F("items__unit_price"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )

        queryset = (
            PurchaseOrder.objects.select_related("seller", "requester")
            .prefetch_related("items", "items__product")
            .order_by("purchase_date")
            .annotate(
                qty_total=Coalesce(Sum("items__quantity"), Value(0)),
                gross_value_db=Coalesce(
                    Sum(line_total),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
            )
        )

        if year:
            queryset = queryset.filter(purchase_date__year=year)

        if date_from:
            queryset = queryset.filter(purchase_date__gte=date_from)

        if date_to:
            queryset = queryset.filter(purchase_date__lte=date_to)

        if selected_sellers:
            queryset = queryset.filter(seller_id__in=selected_sellers)

        if selected_products:
            queryset = queryset.filter(items__product_id__in=selected_products).distinct()

        purchase_orders = list(queryset)

        total_qty = sum((po.qty_total or 0) for po in purchase_orders)
        total_gross = sum((po.gross_value_db or Decimal("0.00")) for po in purchase_orders)
        total_vat = sum((po.vat_amount() or Decimal("0.00")) for po in purchase_orders)
        total_freight = sum((po.freight or Decimal("0.00")) for po in purchase_orders)
        total_amount = sum((po.total_amount() or Decimal("0.00")) for po in purchase_orders)

        chart_labels, chart_totals = self._build_monthly_totals(queryset)

        return dict(
            self.admin_site.each_context(request),
            company=company,
            company_logo_url=request.build_absolute_uri(company.company_logo.url) if company and company.company_logo else "",
            importers=sellers,
            products=products,
            selected_importers=selected_sellers,
            selected_products=selected_products,
            year=year,
            date_from=date_from,
            date_to=date_to,
            purchase_orders=purchase_orders,
            chart_labels=chart_labels,
            chart_totals=chart_totals,
            total_qty=total_qty,
            total_gross=total_gross,
            total_vat=total_vat,
            total_freight=total_freight,
            total_amount=total_amount,
            from_date=date_from,
            to_date=date_to,
            chart_rows=self._build_pdf_chart_rows(chart_labels, chart_totals),
            chart_svg=self._build_pdf_chart_svg(chart_labels, chart_totals, company.currency if company else "EUR"),
            purchase_report_pdf_url=self.get_purchase_report_pdf_url(request),
        )

    def _build_pdf_chart_rows(self, labels, totals):
        if not totals:
            return []

        palette = [
            "#2f7bb0",
            "#49a078",
            "#d98f38",
            "#8b5fbf",
            "#d45d79",
            "#3d5a80",
            "#e9c46a",
            "#2a9d8f",
        ]
        max_total = max(totals) or 1
        rows = []

        for index, (label, total) in enumerate(zip(labels, totals), start=1):
            height_percent = round((total / max_total) * 100, 2) if total else 0
            rows.append({
                "label": label,
                "total": Decimal(str(total)),
                "height_percent": max(6, height_percent) if total else 0,
                "color": palette[(index - 1) % len(palette)],
            })

        return rows

    def _build_pdf_chart_svg(self, labels, totals, currency):
        if not labels or not totals:
            return ""

        width = 920
        height = 300
        left = 62
        right = 20
        top = 18
        bottom = 52
        chart_width = width - left - right
        chart_height = height - top - bottom
        max_total = max(totals) or 1
        count = len(totals)
        slot_width = chart_width / count if count else chart_width
        bar_width = max(28, slot_width * 0.72)

        y_ticks = 5
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" stroke="#bfd0df" stroke-width="1"/>',
            f'<line x1="{left}" y1="{top + chart_height}" x2="{width - right}" y2="{top + chart_height}" stroke="#bfd0df" stroke-width="1"/>',
        ]

        for tick in range(y_ticks + 1):
            ratio = tick / y_ticks
            y = top + chart_height - (chart_height * ratio)
            value = round(max_total * ratio)
            parts.append(
                f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" stroke="#edf2f7" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{left - 8}" y="{y + 4:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#697a8c">{value}</text>'
            )

        for index, (label, total) in enumerate(zip(labels, totals)):
            x = left + (slot_width * index) + ((slot_width - bar_width) / 2)
            bar_height = 0 if max_total == 0 else (total / max_total) * chart_height
            y = top + chart_height - bar_height
            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" fill="#e596a0" stroke="#6c7480" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{x + (bar_width / 2):.2f}" y="{y - 8:.2f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#274257">{round(total)}</text>'
            )
            parts.append(
                f'<text x="{x + (bar_width / 2):.2f}" y="{top + chart_height + 22:.2f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#5d7488">{label}</text>'
            )

        parts.extend([
            f'<text x="{width / 2:.2f}" y="{height - 12}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#697a8c">Month</text>',
            f'<text transform="translate(18 {top + (chart_height / 2):.2f}) rotate(-90)" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#697a8c">Total Amount ({currency})</text>',
            f'<rect x="{width / 2 - 70:.2f}" y="2" width="18" height="8" fill="#e596a0" stroke="#6c7480" stroke-width="1"/>',
            f'<text x="{width / 2 - 46:.2f}" y="10" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#697a8c">Total Amount</text>',
            '</svg>',
        ])
        return "".join(parts)

    def purchase_report(self, request):
        context = self._build_report_context(request)
        return render(request, "admin/purchase/report.html", context)

    def purchase_report_pdf(self, request):
        context = self._build_report_context(request)
        try:
            pdf_bytes = build_purchase_report_pdf(
                company=context.get("company"),
                currency=context.get("company").currency if context.get("company") else "EUR",
                purchase_orders=context.get("purchase_orders", []),
                chart_labels=context.get("chart_labels", []),
                chart_totals=context.get("chart_totals", []),
                total_qty=context.get("total_qty", 0),
                total_gross=context.get("total_gross", Decimal("0.00")),
                total_vat=context.get("total_vat", Decimal("0.00")),
                total_freight=context.get("total_freight", Decimal("0.00")),
                total_amount=context.get("total_amount", Decimal("0.00")),
                from_date=context.get("from_date"),
                to_date=context.get("to_date"),
            )
        except Exception as exc:
            return HttpResponse(
                f"PDF generation failed: {exc}",
                content_type="text/plain; charset=utf-8",
                status=500,
            )

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="purchase-orders-report.pdf"'
        return response

    def _build_monthly_totals(self, queryset):
        monthly_data = (
            queryset.annotate(month=TruncMonth("purchase_date"))
            .values("month")
            .annotate(
                gross_total=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F("items__quantity") * F("items__unit_price"),
                            output_field=DecimalField(max_digits=14, decimal_places=2),
                        )
                    ),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                vat_total=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F("items__quantity") * F("items__unit_price") * F("vat_percent") / Value(100),
                            output_field=DecimalField(max_digits=14, decimal_places=2),
                        )
                    ),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                freight_total=Coalesce(
                    Sum("freight"),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
            )
            .order_by("month")
        )

        labels = []
        totals = []

        for row in monthly_data:
            month = row["month"]
            if not month:
                continue

            total_amount = (row["gross_total"] or Decimal("0.00")) + (row["vat_total"] or Decimal("0.00")) + (row["freight_total"] or Decimal("0.00"))
            labels.append(month.strftime("%Y-%m"))
            totals.append(float(total_amount))

        return labels, totals
