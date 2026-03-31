from decimal import Decimal
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from django import forms
from django.contrib import admin
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import path
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.template.loader import render_to_string
from financeapp.admin_mixins import PageSizeAdminMixin
from financeapp.pdf_rendering import get_pdf_fallback_reason, should_try_weasyprint
from company.models import CompanySetting
from partners.models import Partner
from products.models import Product
from .models import (
    ProformaInvoice,
    CommercialInvoice,
    ProformaInvoiceItem,
    CommercialInvoiceItem
)


# ----------------------
# PROFORMA ITEMS
# ----------------------

class ProformaItemInline(admin.TabularInline):

    model = ProformaInvoiceItem
    extra = 1

    fields = (
        "product",
        "product_description",
        "part_number",
        "stock_info",
        "sale_price_info",
        "purchase_price_info",
        "product_note",
        "quantity",
        "unit_price",
        "total_line",
    )

    readonly_fields = (
        "product_description",
        "part_number",
        "stock_info",
        "sale_price_info",
        "purchase_price_info",
        "product_note",
        "total_line",
    )

    autocomplete_fields = ("product",)

    class Media:
        js = ("admin/js/invoice_product_info.js",)

    def product_description(self, obj):
        value = obj.product.description if obj.product else "-"
        return format_html('<span data-product-field="description">{}</span>', value)

    product_description.short_description = "Description"

    def part_number(self, obj):
        value = obj.product.part_number if obj.product and obj.product.part_number else "-"
        return format_html('<span data-product-field="part_number">{}</span>', value)

    part_number.short_description = "Part Number"

    def stock_info(self, obj):
        value = obj.product.unit_qty if obj.product else "-"
        return format_html('<span data-product-field="stock">{}</span>', value)

    stock_info.short_description = "Stock"

    def sale_price_info(self, obj):
        value = obj.product.sale_price if obj.product else "-"
        return format_html('<span data-product-field="sale_price">{}</span>', value)

    sale_price_info.short_description = "Sale Price"

    def purchase_price_info(self, obj):
        value = obj.product.purchase_price if obj.product else "-"
        return format_html('<span data-product-field="purchase_price">{}</span>', value)

    purchase_price_info.short_description = "Purchase Price"

    def product_note(self, obj):
        value = obj.product.note if obj.product and obj.product.note else "-"
        return format_html('<span data-product-field="note">{}</span>', value)

    product_note.short_description = "Note"


class InvoiceAdminForm(forms.ModelForm):
    class Meta:
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = CompanySetting.objects.first()

        if company and not self.instance.pk:
            if "vat_percent" in self.fields:
                self.fields["vat_percent"].initial = company.vat_amount
            if "invoice_date" in self.fields:
                self.fields["invoice_date"].initial = self._get_default_company_date(company.year)

    def _get_default_company_date(self, year):
        today = timezone.now().date()
        try:
            return today.replace(year=year)
        except ValueError:
            return today.replace(year=year, day=28)


class InvoiceAdminMixin:
    change_form_template = "admin/invoices/change_form.html"
    form = InvoiceAdminForm

    readonly_fields = (
        "invoice_number",
        "subtotal_display",
        "vat_amount_display",
        "total_amount_display",
    )

    class Media:
        js = ("admin/js/invoice_product_info.js",)

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
            not self.has_explicit_year_filter(request, "invoice_date")
        ):
            queryset = queryset.filter(invoice_date__year=company_year)
        return queryset

    def _summary_value(self, key, value):
        return format_html(
            '<span data-invoice-summary="{key}">{value}</span>',
            key=key,
            value=f"{value:.2f}",
        )

    def subtotal_display(self, obj):
        value = obj.subtotal() if obj.pk else 0
        return self._summary_value("subtotal", value)

    subtotal_display.short_description = "Subtotal"

    def vat_amount_display(self, obj):
        value = obj.vat_amount() if obj.pk else 0
        return self._summary_value("vat", value)

    vat_amount_display.short_description = "VAT Amount"

    def total_amount_display(self, obj):
        value = obj.total_amount() if obj.pk else 0
        return self._summary_value("total", value)

    total_amount_display.short_description = "Total Amount"

    def pdf_link(self, obj):
        if not obj.pk:
            return "-"

        return format_html('<a class="button" href="{}" target="_blank">Create PDF</a>', self.get_invoice_pdf_url(obj))

    pdf_link.short_description = "PDF"

    def render_change_form(self, request, context, *args, **kwargs):
        original = context.get("original")
        context["invoice_pdf_url"] = self.get_invoice_pdf_url(original) if original and original.pk else ""
        return super().render_change_form(request, context, *args, **kwargs)

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

    def get_invoice_items_for_pdf(self, obj):
        return [
            {
                "index": index,
                "description": item.product.description if item.product else "-",
                "part_number": item.product.part_number if item.product and item.product.part_number else "-",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_amount": item.total_line(),
            }
            for index, item in enumerate(obj.items.select_related("product"), start=1)
        ]

    def get_invoice_hs_code(self, obj):
        return getattr(obj, "hs_code", "") or "-"

    def get_invoice_title(self):
        return self.model._meta.verbose_name.replace("_", " ").title()

    def get_invoice_pdf_filename(self, obj):
        return f"{obj.invoice_number or self.model._meta.model_name}.pdf"

    def get_invoice_pdf_url(self, obj):
        return reverse(f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_pdf", args=[obj.pk])

    def get_invoice_pdf_context(self, request, obj):
        company = CompanySetting.objects.first()
        return {
            "invoice": obj,
            "invoice_title": self.get_invoice_title(),
            "is_proforma": isinstance(obj, ProformaInvoice),
            "company": company,
            "company_logo_url": request.build_absolute_uri(company.company_logo.url) if company and company.company_logo else "",
            "importer": self.build_partner_context(obj.importer),
            "end_user": self.build_partner_context(obj.end_user),
            "items": self.get_invoice_items_for_pdf(obj),
            "hs_code": self.get_invoice_hs_code(obj),
            "currency": company.currency if company else "EUR",
            "subtotal": obj.subtotal(),
            "vat_amount": obj.vat_amount(),
            "total_amount": obj.total_amount(),
            "render_as_html": False,
            "pdf_error": "",
        }

    def _build_pdf_with_weasyprint(self, html_string, base_url):
        from weasyprint import HTML

        return HTML(
            string=html_string,
            base_url=base_url,
        ).write_pdf()

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

    def _build_pdf_with_xhtml2pdf(self, html_string):
        from xhtml2pdf import pisa

        result = BytesIO()
        pdf = pisa.CreatePDF(
            src=html_string,
            dest=result,
            link_callback=self._pdf_link_callback,
        )
        if pdf.err:
            raise RuntimeError("xhtml2pdf could not render the invoice document.")
        return result.getvalue()

    def export_pdf(self, request, object_id):
        obj = get_object_or_404(
            self.model.objects.select_related("importer", "end_user").prefetch_related(
                "items__product",
                "importer__addresses",
                "importer__phones",
                "end_user__addresses",
                "end_user__phones",
            ),
            pk=object_id,
        )

        context = self.get_invoice_pdf_context(request, obj)
        html_string = render_to_string("admin/invoices/pdf.html", context)
        try:
            if not should_try_weasyprint():
                raise OSError(get_pdf_fallback_reason())

            pdf_bytes = self._build_pdf_with_weasyprint(
                html_string=html_string,
                base_url=request.build_absolute_uri("/"),
            )
        except (ImportError, OSError):
            try:
                pdf_bytes = self._build_pdf_with_xhtml2pdf(html_string)
            except Exception as exc:
                context["render_as_html"] = True
                context["pdf_error"] = (
                    "PDF generation is unavailable because both installed renderers failed. "
                    "This printable HTML fallback is shown instead."
                )
                context["pdf_error_details"] = str(exc)
                fallback_html = render_to_string("admin/invoices/pdf.html", context)
                return HttpResponse(fallback_html)
        except Exception as exc:
            context["render_as_html"] = True
            context["pdf_error"] = "PDF generation failed unexpectedly. This printable HTML fallback is shown instead."
            context["pdf_error_details"] = str(exc)
            fallback_html = render_to_string("admin/invoices/pdf.html", context)
            return HttpResponse(fallback_html)

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{self.get_invoice_pdf_filename(obj)}"'
        return response


# ----------------------
# PROFORMA ADMIN
# ----------------------

@admin.register(ProformaInvoice)
class ProformaInvoiceAdmin(InvoiceAdminMixin, PageSizeAdminMixin, admin.ModelAdmin):
    changelist_template = "admin/invoices/change_list.html"

    fieldsets = (
        ("Invoice Overview", {
            "fields": (
                ("invoice_date", "invoice_number"),
                "importer",
                "end_user",
                ("hs_code", "our_reference"),
            )
        }),
        ("Financial Summary", {
            "fields": (
                ("freight", "discount", "vat_percent"),
                ("subtotal_display", "vat_amount_display"),
                "total_amount_display",
            )
        }),
    )

    inlines = [ProformaItemInline]

    actions = ["convert_to_commercial"]

    list_display = (
        "id",
        "proforma_number",
        "invoice_date_display",
        "importer",
        "end_user",
        "hs_code_display",
        "amount_display",
        "pdf_link",
    )

    ordering = ("-invoice_date",)

    autocomplete_fields = (
        "importer",
        "end_user",
    )

    search_fields = (
        "invoice_number",
        "importer__description",
        "end_user__description",
    )

    list_filter = (
        "invoice_date",
        "importer",
    )

    # ----------------------
    # DATE DISPLAY
    # ----------------------

    def invoice_date_display(self, obj):

        if obj.invoice_date:
            return obj.invoice_date.strftime("%Y-%m-%d")

        return "-"

    invoice_date_display.short_description = "Date"
    invoice_date_display.admin_order_field = "invoice_date"

    # ----------------------
    # HS CODE DISPLAY
    # ----------------------

    def hs_code_display(self, obj):
        if obj.hs_code:
            return obj.hs_code

        return "Not specified"

    hs_code_display.short_description = "HS Code"

    # ----------------------
    # NUMBER
    # ----------------------

    def proforma_number(self, obj):

        return obj.invoice_number

    proforma_number.short_description = "Proforma Number"
    proforma_number.admin_order_field = "invoice_number"

    # ----------------------
    # AMOUNT
    # ----------------------

    def amount_display(self, obj):

        return obj.total_amount()

    amount_display.short_description = "Amount"

    # ----------------------
    # ACTION
    # ----------------------

    def convert_to_commercial(self, request, queryset):

        for proforma in queryset:

            if hasattr(proforma, "convert_to_commercial"):
                proforma.convert_to_commercial()

    convert_to_commercial.short_description = "Convert to Commercial Invoice"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/pdf/",
                self.admin_site.admin_view(self.export_pdf),
                name="invoices_proformainvoice_pdf",
            ),
        ]
        return custom_urls + urls


# ----------------------
# COMMERCIAL ITEMS
# ----------------------

class CommercialItemInline(admin.TabularInline):

    model = CommercialInvoiceItem
    extra = 1

    fields = (
        "product",
        "product_description",
        "part_number",
        "stock_info",
        "sale_price_info",
        "purchase_price_info",
        "product_note",
        "quantity",
        "unit_price",
        "total_line",
    )

    readonly_fields = (
        "product_description",
        "part_number",
        "stock_info",
        "sale_price_info",
        "purchase_price_info",
        "product_note",
        "total_line",
    )

    autocomplete_fields = ("product",)

    class Media:
        js = ("admin/js/invoice_product_info.js",)

    def product_description(self, obj):
        value = obj.product.description if obj.product else "-"
        return format_html('<span data-product-field="description">{}</span>', value)

    product_description.short_description = "Description"

    def part_number(self, obj):
        value = obj.product.part_number if obj.product and obj.product.part_number else "-"
        return format_html('<span data-product-field="part_number">{}</span>', value)

    part_number.short_description = "Part Number"

    def stock_info(self, obj):
        value = obj.product.unit_qty if obj.product else "-"
        return format_html('<span data-product-field="stock">{}</span>', value)

    stock_info.short_description = "Stock"

    def sale_price_info(self, obj):
        value = obj.product.sale_price if obj.product else "-"
        return format_html('<span data-product-field="sale_price">{}</span>', value)

    sale_price_info.short_description = "Sale Price"

    def purchase_price_info(self, obj):
        value = obj.product.purchase_price if obj.product else "-"
        return format_html('<span data-product-field="purchase_price">{}</span>', value)

    purchase_price_info.short_description = "Purchase Price"

    def product_note(self, obj):
        value = obj.product.note if obj.product and obj.product.note else "-"
        return format_html('<span data-product-field="note">{}</span>', value)

    product_note.short_description = "Note"


# ----------------------
# COMMERCIAL ADMIN
# ----------------------

@admin.register(CommercialInvoice)
class CommercialInvoiceAdmin(InvoiceAdminMixin, PageSizeAdminMixin, admin.ModelAdmin):
    changelist_template = "admin/invoices/change_list.html"

    fieldsets = (
        ("Invoice Overview", {
            "fields": (
                ("invoice_date", "invoice_number"),
                "importer",
                "end_user",
                ("our_order_no", "our_reference"),
            )
        }),
        ("Financial Summary", {
            "fields": (
                ("freight", "discount", "vat_percent"),
                ("subtotal_display", "vat_amount_display"),
                "total_amount_display",
            )
        }),
    )

    inlines = [CommercialItemInline]

    list_display = (
        "id",
        "commercial_number",
        "invoice_date_display",
        "importer",
        "end_user",
        "hs_code_display",
        "amount_display",
        "pdf_link",
    )

    ordering = ("-invoice_date",)

    autocomplete_fields = (
        "importer",
        "end_user",
    )

    search_fields = (
        "invoice_number",
        "importer__description",
        "end_user__description",
    )

    list_filter = (
        "invoice_date",
        "importer",
    )

    # ----------------------
    # DATE DISPLAY
    # ----------------------

    def invoice_date_display(self, obj):

        if obj.invoice_date:
            return obj.invoice_date.strftime("%Y-%m-%d")

        return "-"

    invoice_date_display.short_description = "Date"
    invoice_date_display.admin_order_field = "invoice_date"

    # ----------------------
    # HS CODE DISPLAY
    # ----------------------

    def hs_code_display(self, obj):

        item = obj.items.first()

        if item and item.hs_code:
            return item.hs_code

        return "Not specified"

    hs_code_display.short_description = "HS Code"

    def get_invoice_hs_code(self, obj):
        item = obj.items.first()
        if item and item.hs_code:
            return item.hs_code
        return "-"

    # ----------------------
    # NUMBER
    # ----------------------

    def commercial_number(self, obj):

        return obj.invoice_number

    commercial_number.short_description = "Commercial Number"
    commercial_number.admin_order_field = "invoice_number"

    # ----------------------
    # AMOUNT
    # ----------------------

    def amount_display(self, obj):

        return obj.total_amount()

    amount_display.short_description = "Amount"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/pdf/",
                self.admin_site.admin_view(self.export_pdf),
                name="invoices_commercialinvoice_pdf",
            ),
            path(
                "report/",
                self.admin_site.admin_view(self.commercial_report),
                name="commercial_invoice_report",
            ),
        ]
        return custom_urls + urls

    def commercial_report(self, request):
        importers = Partner.objects.filter(partner_type="importer").order_by("description")
        products = Product.objects.all().order_by("description")

        selected_importers = request.GET.getlist("importers")
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
        vat_total_expr = ExpressionWrapper(
            F("items__quantity") * F("items__unit_price") * F("vat_percent") / Value(100),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )

        queryset = (
            CommercialInvoice.objects.select_related("importer", "end_user")
            .prefetch_related("items", "items__product")
            .order_by("invoice_date")
            .annotate(
                qty_total=Coalesce(Sum("items__quantity"), Value(0)),
                subtotal_db=Coalesce(
                    Sum(line_total),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                vat_amount_db=Coalesce(
                    Sum(vat_total_expr),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
            )
        )

        if year:
            queryset = queryset.filter(invoice_date__year=year)

        if date_from:
            queryset = queryset.filter(invoice_date__gte=date_from)

        if date_to:
            queryset = queryset.filter(invoice_date__lte=date_to)

        if selected_importers:
            queryset = queryset.filter(importer_id__in=selected_importers)

        if selected_products:
            queryset = queryset.filter(items__product_id__in=selected_products).distinct()

        invoices = list(queryset)

        total_qty = sum((invoice.qty_total or 0) for invoice in invoices)
        total_subtotal = sum((invoice.subtotal_db or Decimal("0.00")) for invoice in invoices)
        total_vat = sum((invoice.vat_amount() or Decimal("0.00")) for invoice in invoices)
        total_freight = sum((invoice.freight or Decimal("0.00")) for invoice in invoices)
        total_discount = sum((invoice.discount or Decimal("0.00")) for invoice in invoices)
        total_amount = sum((invoice.total_amount() or Decimal("0.00")) for invoice in invoices)

        chart_labels, chart_totals = self._build_monthly_totals(queryset)

        context = dict(
            self.admin_site.each_context(request),
            importers=importers,
            products=products,
            selected_importers=selected_importers,
            selected_products=selected_products,
            year=year,
            date_from=date_from,
            date_to=date_to,
            invoices=invoices,
            chart_labels=chart_labels,
            chart_totals=chart_totals,
            total_qty=total_qty,
            total_subtotal=total_subtotal,
            total_vat=total_vat,
            total_freight=total_freight,
            total_discount=total_discount,
            total_amount=total_amount,
            from_date=date_from,
            to_date=date_to,
        )

        return render(request, "admin/invoices/commercial_report.html", context)

    def _build_monthly_totals(self, queryset):
        monthly_data = (
            queryset.annotate(month=TruncMonth("invoice_date"))
            .values("month")
            .annotate(
                subtotal_total=Coalesce(
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
                discount_total=Coalesce(
                    Sum("discount"),
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

            total_amount = (
                (row["subtotal_total"] or Decimal("0.00"))
                + (row["vat_total"] or Decimal("0.00"))
                + (row["freight_total"] or Decimal("0.00"))
                - (row["discount_total"] or Decimal("0.00"))
            )
            labels.append(month.strftime("%Y-%m"))
            totals.append(float(total_amount))

        return labels, totals
